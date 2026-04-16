"""
AgentRunner — The execution engine for all AI agents.

Lifecycle of a single agent execution:
  1. Create AgentExecutionLog (status=STARTED)
  2. Build context from DB
  3. Construct system prompt with company context + custom instructions
  4. Call OpenAI via LLM client
  5. Parse structured output
  6. Evaluate each action against autonomy threshold
  7. Execute autonomous actions immediately
  8. Queue non-autonomous actions into ApprovalRequest
  9. Update AgentExecutionLog (status=COMPLETED or AWAITING_APPROVAL)
  10. Dispatch notifications
"""
import logging
from django.utils import timezone
from django.conf import settings

from apps.agents.models import AgentExecutionLog, AgentConfiguration, AgentType
from .client import call_llm, BudgetExhaustedError, LLMCallError
from .context import (
    build_company_context,
    build_operations_context,
    build_support_context,
    build_sales_context,
    format_context_for_prompt,
)
from .prompts import get_system_prompt

logger = logging.getLogger("apps.agents")


class AgentRunner:
    """
    Runs a single agent execution for a given company.
    Instantiate, then call .run().
    """

    def __init__(
        self,
        agent_type: str,
        company,
        task_description: str,
        trigger_source: str,
        triggered_by=None,
        extra_context: dict = None,
    ):
        self.agent_type = agent_type
        self.company = company
        self.task_description = task_description
        self.trigger_source = trigger_source
        self.triggered_by = triggered_by
        self.extra_context = extra_context or {}
        self.log = None
        self.config = self._load_config()

    def _load_config(self) -> AgentConfiguration:
        config, _ = AgentConfiguration.objects.get_or_create(
            company=self.company,
            agent_type=self.agent_type,
            defaults={"autonomy_level": settings.AGENT_DEFAULT_AUTONOMY},
        )
        return config

    def run(self) -> AgentExecutionLog:
        """
        Main execution method. Returns the completed AgentExecutionLog.
        """
        if not self.config.is_enabled:
            logger.info("Agent %s is disabled for company %s", self.agent_type, self.company.name)
            return None

        # Step 1: Create execution log
        self.log = AgentExecutionLog.objects.create(
            company=self.company,
            agent_type=self.agent_type,
            status=AgentExecutionLog.Status.STARTED,
            trigger_source=self.trigger_source,
            triggered_by=self.triggered_by,
            task_description=self.task_description,
        )

        try:
            # Step 2: Build context
            context = self._build_context()
            self.log.input_context = context
            self.log.save(update_fields=["input_context"])

            # Step 3: Construct prompt
            company_ctx = build_company_context(self.company)
            context_str = format_context_for_prompt(context)
            prompt_vars = {
                **company_ctx,
                "context": context_str,
                "custom_instructions": self.config.custom_instructions or "",
            }
            system_prompt = get_system_prompt(self.agent_type, prompt_vars)

            # Step 4: Call LLM
            llm_result = call_llm(
                system_prompt=system_prompt,
                user_message=self.task_description,
                company=self.company,
                response_schema=True,
            )

            # Step 5: Update log with LLM output
            self.log.llm_response = llm_result.content
            self.log.parsed_output = llm_result.parsed
            self.log.confidence_score = llm_result.parsed.get("confidence_score")
            self.log.prompt_tokens = llm_result.prompt_tokens
            self.log.completion_tokens = llm_result.completion_tokens
            self.log.total_tokens = llm_result.total_tokens

            # Step 6-8: Process actions
            actions_taken = []
            has_pending_approvals = False

            for action in llm_result.parsed.get("actions", []):
                result = self._process_action(action)
                action["_result"] = result
                actions_taken.append(action)
                if result == "queued_for_approval":
                    has_pending_approvals = True

            self.log.actions_taken = actions_taken

            # Step 9: Finalize log status
            final_status = (
                AgentExecutionLog.Status.AWAITING_APPROVAL
                if has_pending_approvals
                else AgentExecutionLog.Status.COMPLETED
            )
            self.log.status = final_status
            self.log.completed_at = timezone.now()
            self.log.save()

            logger.info(
                "Agent %s completed | company=%s | actions=%d | pending_approvals=%s",
                self.agent_type,
                self.company.name,
                len(actions_taken),
                has_pending_approvals,
            )

            # Step 10: Dispatch result notifications
            self._dispatch_result_notification(llm_result.parsed)

        except BudgetExhaustedError as e:
            self._fail(str(e))
        except LLMCallError as e:
            self._fail(str(e))
        except Exception as e:
            logger.exception("Unexpected error in AgentRunner for %s", self.agent_type)
            self._fail(str(e))

        return self.log

    def _build_context(self) -> dict:
        """Select and build the context appropriate for this agent type."""
        builders = {
            AgentType.OPERATIONS: build_operations_context,
            AgentType.CUSTOMER_SUPPORT: build_support_context,
            AgentType.SALES: build_sales_context,
        }
        builder = builders.get(self.agent_type, lambda c: {})
        context = builder(self.company)
        context.update(self.extra_context)
        return context

    def _process_action(self, action: dict) -> str:
        """
        Evaluate one action from the LLM output.
        Returns: "executed" | "queued_for_approval" | "skipped"
        """
        requires_approval = action.get("requires_approval", True)
        confidence = self.log.confidence_score or 0.0

        # Force approval if confidence is below threshold
        if confidence < settings.AGENT_CONFIDENCE_THRESHOLD:
            requires_approval = True

        # Force approval if autonomy level is low enough
        autonomy = self.config.autonomy_level
        if autonomy < 0.5 and action.get("priority") in ("high", "critical"):
            requires_approval = True

        if requires_approval:
            self._create_approval_request(action)
            return "queued_for_approval"
        else:
            return self._execute_action(action)

    def _execute_action(self, action: dict) -> str:
        """
        Execute an action autonomously (no human approval needed).
        Currently handles notification dispatch. More action types in Phase 2.
        """
        action_type = action.get("type", "")

        if action_type == "notify_team":
            from apps.notifications.services import dispatch_agent_notification
            dispatch_agent_notification(
                company=self.company,
                title=action.get("description", "Agent Update"),
                body=self.log.parsed_output.get("summary", ""),
                agent_type=self.agent_type,
            )
            return "executed"

        elif action_type == "generate_report":
            # Reports are written to the execution log — no further action needed
            return "executed"

        else:
            logger.warning("Unknown autonomous action type: %s", action_type)
            return "skipped"

    def _create_approval_request(self, action: dict):
        """
        Write an ApprovalRequest record and notify the relevant team members.
        """
        from apps.approvals.models import ApprovalRequest
        from datetime import timedelta

        expiry = timezone.now() + timedelta(hours=settings.AGENT_APPROVAL_EXPIRY_HOURS)

        approval = ApprovalRequest.objects.create(
            company=self.company,
            agent_type=self.agent_type,
            execution_log=self.log,
            action_category=ApprovalRequest.ActionCategory.TASK_MANAGEMENT,
            action_type=action.get("type", "unknown"),
            action_payload=action.get("payload", {}),
            title=action.get("description", "Agent action requires approval"),
            reasoning=self.log.parsed_output.get("summary", ""),
            confidence_score=self.log.confidence_score or 0.0,
            expires_at=expiry,
        )

        # Notify approvers via Telegram + in-app
        from apps.notifications.services import dispatch_approval_notification
        dispatch_approval_notification(company=self.company, approval=approval)

    def _dispatch_result_notification(self, parsed_output: dict):
        """Send summary notification after agent run completes."""
        alerts = parsed_output.get("alerts", [])
        if alerts:
            from apps.notifications.services import dispatch_agent_notification
            dispatch_agent_notification(
                company=self.company,
                title=f"{self.agent_type.replace('_', ' ').title()} Alert",
                body="\n".join(str(a) for a in alerts),
                agent_type=self.agent_type,
                priority="high",
            )

    def _fail(self, error_message: str):
        """Mark the execution log as failed."""
        if self.log:
            self.log.status = AgentExecutionLog.Status.FAILED
            self.log.error_message = error_message
            self.log.completed_at = timezone.now()
            self.log.save()
        logger.error("Agent %s FAILED: %s", self.agent_type, error_message)
