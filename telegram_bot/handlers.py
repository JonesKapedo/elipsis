import math

from aiogram import types
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from telegram_bot.scoring import ScoringInputError, assess
from constants import BRAND_NAME, INDEX_NAME, INDEX_SHORT, CURRENCY


class QStates(StatesGroup):
    q1 = State()
    q2 = State()
    q3 = State()


def _parse_number(text, allow_float=False):
    """Return a non-negative number parsed from free text, or None."""
    if not text:
        return None
    cleaned = str(text).strip().replace(",", "").replace("%", "")
    try:
        value = float(cleaned)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    if not allow_float:
        if not value.is_integer():
            return None
        value = int(value)
    return value if value >= 0 else None


async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"Welcome to {BRAND_NAME}.\n\n"
        f"I'll help you understand your team's readiness for automation — "
        f"gently, in about a minute.\n\n"
        f"How many repetitive tasks does your team handle each week?"
    )
    await state.set_state(QStates.q1)


async def answer_handler(message: types.Message, state: FSMContext):
    state_name = await state.get_state()
    if state_name is None:
        await message.answer(f"Send /start to begin your {INDEX_SHORT} check.")
        return

    if state_name == QStates.q1.state:
        value = _parse_number(message.text)
        if value is None:
            await message.answer("I didn't catch a number there. "
                                 "Please reply with a whole number, e.g. 20.")
            return
        await state.update_data(tasks_per_week=value)
        await message.answer("On average, how many minutes does each task take?")
        await state.set_state(QStates.q2)
        return

    if state_name == QStates.q2.state:
        value = _parse_number(message.text, allow_float=True)
        if value is None:
            await message.answer("I didn't catch a number there. "
                                 "Please reply with minutes, e.g. 15.")
            return
        await state.update_data(minutes_per_task=value)
        await message.answer("And how many people perform these tasks?")
        await state.set_state(QStates.q3)
        return

    if state_name == QStates.q3.state:
        value = _parse_number(message.text)
        if value is None or value < 1:
            await message.answer("Please reply with the number of people, e.g. 3.")
            return
        await state.update_data(staff=value)
        data = await state.get_data()
        try:
            summary = "\n".join(assess(data).summary_lines(CURRENCY))
        except ScoringInputError:
            await state.clear()
            await message.answer("Something in those answers didn't add up. "
                                 "Send /start to try again.")
            return
        await message.answer(
            f"Thank you — here is your preliminary {INDEX_SHORT}.\n\n"
            f"{summary}\n\n"
            f"This is an early indicator only. A full {INDEX_NAME} looks at the "
            f"whole department across all seven readiness pillars."
        )
        await state.clear()
