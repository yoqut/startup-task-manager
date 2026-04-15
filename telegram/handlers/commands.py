from telegram.keyboards.inlines import tariff_inl
from telegram.loader import handle

@handle(commands=["start"])
async def start(sender, state):
    await state.delete()
    lang = sender.lang
    await sender.text("wellcome", markup=tariff_inl(lang),  name=sender.user.full_name)

