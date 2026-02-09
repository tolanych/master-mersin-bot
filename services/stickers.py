from aiogram.types import Message
from aiogram.fsm.context import FSMContext
import logging

logger = logging.getLogger(__name__)

class StickerEvent:
    WELCOME = "welcome"
    CATEGORIES = "categories"
    SEARCHING = "searching"
    MASTER_FOUND = "master_found"
    CONTACT = "contact"
    ORDER_STARTED = "order_started"
    FEEDBACK = "feedback"
    SUCCESS = "success"
    ERROR = "error"
    EMPTY = "empty"
    PREMIUM = "premium"
    DONE = "done"

STICKERS = {
    StickerEvent.WELCOME: "CAACAgQAAxkBAAFCBsRpiOeyaRymvpm8aCf4Q4J-83IOXQACPB8AAgH-2VOKwZSZKzhIeDoE",
    StickerEvent.CATEGORIES: "CAACAgQAAxkBAAFCCMxpiRspRkRHpB0i8Ib5VnBCYVyEfgACNh0AAgip2VPoo-JemHCUyzoE",
    StickerEvent.SEARCHING: "CAACAgQAAxkBAAFCCM5piRs2WDGvPr-ElR4UXSkC1-g1bwACqR0AAo1j0VMLLckVfdqndToE",
    StickerEvent.MASTER_FOUND: "CAACAgQAAxkBAAFCCNNpiRtGPJi0KrvjFGVu_8E9zXc35QACThsAAv-O2FPVnuGTsrNwZDoE",
    StickerEvent.CONTACT: "CAACAgQAAxkBAAFCCNZpiRtSDd2kbzXwzbnAEwKXKEWVxQACfx8AAmo92FM87NcPwoaZdDoE",
    StickerEvent.ORDER_STARTED: "CAACAgQAAxkBAAFCCNhpiRtjbwQYA-kqK1lql-AVUTMsmAACKxsAAqk10FPT720PI6FzfToE",
    StickerEvent.FEEDBACK: "CAACAgQAAxkBAAFCCNxpiRttspIElMKh9yQjVq38xCXa5QACExwAAnhk0FMTL54YqpozKToE",
    StickerEvent.SUCCESS: "CAACAgQAAxkBAAFCCN5piRt7jPEYFXpqsabUKspGAAHGGd8AAvMdAALJ59FTnzRslvFUlwM6BA",
    StickerEvent.ERROR: "CAACAgQAAxkBAAFCCOJpiRuTFqGKDqZf304e5rAWcBSi6gACZSMAAl1M2VNw7Uo3yInanToE",
    StickerEvent.EMPTY: "CAACAgQAAxkBAAFCCORpiRugAXIdQj09vzZRu_WmOX_ymgACixsAAglU2FM_SQ0pKJ0NlzoE",
    StickerEvent.PREMIUM: "CAACAgQAAxkBAAFCCOBpiRuI85JsfNaB3EIzziZkW3VUXgACayEAAmK20FNnuMJi395N2zoE",
    StickerEvent.DONE: "CAACAgQAAxkBAAFCCOhpiRusATd-z7v707eOuYv-ylO7dQACkRkAAlhK0FOpyuR26ktSyjoE",
}

async def replace_sticker(message: Message, state: FSMContext, key: str):
    """
    Replaces the previous sticker with a new one based on the key.
    Stores the new sticker message ID in the FSM state.
    """
    sticker_id = STICKERS.get(key)
    if not sticker_id:
        logger.warning(f"Sticker key '{key}' not found in STICKERS dict.")
        return

    data = await state.get_data()
    old_sticker_msg_id = data.get("sticker_msg_id")

    # Delete old sticker if it exists
    if old_sticker_msg_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=old_sticker_msg_id)
        except Exception as e:
            logger.warning(f"Failed to delete old sticker: {e}")

    # Send new sticker
    try:
        new_sticker_msg = await message.answer_sticker(sticker_id)
        await state.update_data(sticker_msg_id=new_sticker_msg.message_id)
    except Exception as e:
        logger.error(f"Failed to send new sticker: {e}")


async def clear_state_preserve_sticker(state: FSMContext):
    """
    Clears the FSM state while preserving sticker_msg_id.
    Use this instead of state.clear() to maintain sticker tracking.
    """
    data = await state.get_data()
    sticker_msg_id = data.get("sticker_msg_id")
    await state.clear()
    if sticker_msg_id:
        await state.update_data(sticker_msg_id=sticker_msg_id)
