
async def safe_finish(state):
    try:
        await state.clear()
    except Exception:
        pass
