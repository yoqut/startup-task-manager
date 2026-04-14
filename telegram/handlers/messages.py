from ...loader import handle

@handle(commands=["start"])
async def start(sender, state):
    await state.delete()
    await sender.text("wellcome")