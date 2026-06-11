async def cb_categories(call: CallbackQuery):
        await call.message.edit_text("ÐÑÐ±ÐµÑÐ¸ÑÐµ ÐºÐ°ÑÐµÐ³Ð¾ÑÐ¸Ñ:", reply_markup=categories_kb())
        await call.answer()

    @dp.callback_query(F.data == "storage")
    async def cb_storage(call: CallbackQuery):
        await call.message.edit_text("ð Ð¡ÑÐ¾ÐºÐ¸ ÑÑÐ°Ð½ÐµÐ½Ð¸Ñ:", reply_markup=item_list_kb("ð Ð¡ÑÐ¾ÐºÐ¸ ÑÑÐ°Ð½ÐµÐ½Ð¸Ñ"))
        await call.answer()

    @dp.callback_query(F.data.startswith("cat:"))
    async def cb_cat(call: CallbackQuery):
        cat = call.data.split(":", 1)[1]
        await call.message.edit_text(f"<b>{cat}</b>\nÐÑÐ±ÐµÑÐ¸ÑÐµ Ð¿Ð¾Ð·Ð¸ÑÐ¸Ñ:", reply_markup=item_list_kb(cat))
        await call.answer()

    @dp.callback_query(F.data.startswith("item:"))
    async def cb_item(call: CallbackQuery):
        item_id = int(call.data.split(":", 1)[1])
        row = get_item(item_id)
        if not row:
            await call.answer("ÐÐµ Ð½Ð°Ð¹Ð´ÐµÐ½Ð¾", show_alert=True)
            return
        await call.message.edit_text(format_item(row), reply_markup=item_kb(item_id))
        await call.answer()

    @dp.callback_query(F.data.startswith("fav:"))
    async def cb_fav(call: CallbackQuery):
        item_id = int(call.data.split(":", 1)[1])
        conn = db()
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO favorites(user_id,item_id) VALUES(?,?)",
            (call.from_user.id, item_id),
        )
        conn.commit()
        conn.close()
        await call.answer("ÐÐ¾Ð±Ð°Ð²Ð»ÐµÐ½Ð¾ Ð² Ð¸Ð·Ð±ÑÐ°Ð½Ð½Ð¾Ðµ â­")

    @dp.callback_query(F.data == "favorites")
    async def cb_favorites(call: CallbackQuery):
        conn = db()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT i.id, i.name
            FROM items i
            JOIN favorites f ON i.id=f.item_id
            WHERE f.user_id=?
            ORDER BY i.name
            """,
            (call.from_user.id,),
        )
        rows = cur.fetchall()
        conn.close()

        if not rows:
            await call.message.edit_text("ÐÐ·Ð±ÑÐ°Ð½Ð½Ð¾Ðµ Ð¿Ð¾ÐºÐ° Ð¿ÑÑÑÐ¾Ðµ.", reply_markup=main_menu_kb())
        else:
            kb = InlineKeyboardBuilder()
            for item_id, name in rows:
                kb.button(text=name, callback_data=f"item:{item_id}")
            kb.button(text="ð  Ð¡ÑÐ°ÑÑ", callback_data="home")
            kb.adjust(1)
            await call.message.edit_text("â­ ÐÐ·Ð±ÑÐ°Ð½Ð½Ð¾Ðµ:", reply_markup=kb.as_markup())

        await call.answer()

    @dp.callback_query(F.data == "search_help")
    async def cb_search_help(call: CallbackQuery):
        await call.message.edit_text(
            "ð ÐÐ°Ð¿Ð¸ÑÐ¸ÑÐµ Ð² ÑÐ°Ñ Ð½Ð°Ð·Ð²Ð°Ð½Ð¸Ðµ Ð½Ð°Ð¿Ð¸ÑÐºÐ° Ð¸Ð»Ð¸ ÑÐ°ÑÑÑ Ð½Ð°Ð·Ð²Ð°Ð½Ð¸Ñ.\n"
            "ÐÐ°Ð¿ÑÐ¸Ð¼ÐµÑ: <b>Ð¼Ð°ÑÑÐ°</b>, <b>ÑÑÑÐ½ÑÐ¹</b>, <b>Ð»Ð¸Ð¼Ð¾Ð½Ð°Ð´</b>.",
            reply_markup=main_menu_kb(),
        )
        await call.answer()

    @dp.message(F.text)
    async def text_search(message: Message):
        rows = search_items(message.text.strip())

        if not rows:
            await message.answer(
                "ÐÐ¸ÑÐµÐ³Ð¾ Ð½Ðµ Ð½Ð°Ð¹Ð´ÐµÐ½Ð¾. ÐÐ¾Ð¿ÑÐ¾Ð±ÑÐ¹ÑÐµ Ð´ÑÑÐ³Ð¾Ðµ Ð½Ð°Ð·Ð²Ð°Ð½Ð¸Ðµ Ð¸Ð»Ð¸ Ð¾ÑÐºÑÐ¾Ð¹ÑÐµ Ð¼ÐµÐ½Ñ.",
                reply_markup=main_menu_kb(),
            )
            return

        kb = InlineKeyboardBuilder()
        for item_id, name, category in rows:
            kb.button(text=f"{name} â {category}", callback_data=f"item:{item_id}")
        kb.adjust(1)

        await message.answer("ÐÐ°ÑÐ»Ð° Ð²Ð°ÑÐ¸Ð°Ð½ÑÑ:", reply_markup=kb.as_markup())

    await dp.start_polling(bot)


if name == "__main__":
    asyncio.run(main())
