from telegram.loader import handle

@handle(commands=["start"])
async def start(sender, state):
    await state.delete()
    await sender.text("wellcome", name=sender.user.full_name)