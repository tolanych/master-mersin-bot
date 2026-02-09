
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from aiogram.fsm.context import FSMContext
import logging

import globals
from keyboards import get_order_completion_keyboard

logger = logging.getLogger(__name__)

class OrderCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        
        user_id = None
        message = None

        if isinstance(event, Message):
            user_id = event.chat.id
            message = event
        elif isinstance(event, CallbackQuery):
            user_id = event.message.chat.id
            message = event.message

        if not user_id:
            data["user"] = None
            return await handler(event, data)
            
        db = globals.get_db()
        # Look for user database ID
        user = await db.get_user_by_tg_id(user_id)
        
        # Inject user into data for handlers
        data["user"] = user
        # Check FSM state - allow review-related states to pass through
        state: FSMContext = data.get("state")

        if state:
            current_state = await state.get_state()
            if current_state:
                # Allow all ClientReview and MasterRateClient states to pass through
                if (current_state.startswith("ClientReview:") or 
                    current_state.startswith("MasterRateClient:")):
                    return await handler(event, data)

        if isinstance(event, CallbackQuery):
            # Allow completion actions to pass through
            if event.data and (
                event.data.startswith("order_complete_") or 
                event.data.startswith("review_") or
                event.data == "order_problem" # assuming there might be a problem report button
            ):
                return await handler(event, data)
 
        if not user:
            # New user, no orders
            return await handler(event, data)
            
        pending_order = await db.get_client_pending_order(user['id'])
        
        if pending_order:
            logger.info(f"User {user_id} blocked due to pending order {pending_order['id']}")
            lang = user['language']
            
            # Localize text
            # We construct the message manually or use get_text if we add keys
            text = f"⚠️ <b>Внимание!</b>\n\n"
            text += f"У вас есть незавершенный заказ более 24 часов.\n"
            text += f"Пожалуйста, завершите его, чтобы продолжить использование бота.\n\n"
            text += f"🛠 <b>Мастер:</b> {pending_order['master_name']}\n"
            text += f"📞 <b>Телефон:</b> {pending_order['master_phone']}\n"
            
            # Send warning
            try:
                if isinstance(event, CallbackQuery):
                    await event.answer("Завершите активный заказ!", show_alert=True)
                    await message.edit_text(text, reply_markup=get_order_completion_keyboard(pending_order['id'], lang))
                else:
                    await message.answer(text, reply_markup=get_order_completion_keyboard(pending_order['id'], lang))
            except Exception as e:
                logger.error(f"Failed to send block message: {e}")
                
            # Stop propagation
            return
            
        return await handler(event, data)
