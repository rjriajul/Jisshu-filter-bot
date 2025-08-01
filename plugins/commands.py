import os
import requests
import logging
import random
import asyncio
import string
import pytz
from datetime import datetime as dt
from Script import script
from pyrogram import Client, filters, enums
from pyrogram.errors import ChatAdminRequired
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from database.ia_filterdb import (
    Media,
    get_file_details,
    get_bad_files,
    unpack_new_file_id,
)
from database.users_chats_db import db
from database.config_db import mdb
from database.topdb import JsTopDB
from database.jsreferdb import referdb
from plugins.pm_filter import auto_filter
from utils import (
    formate_file_name,
    get_settings,
    save_group_settings,
    is_req_subscribed,
    is_subscribed,
    get_size,
    get_shortlink,
    is_check_admin,
    get_status,
    temp,
    get_readable_time,
    save_default_settings,
)
import re
import base64
from info import *

logger = logging.getLogger(__name__)
movie_series_db = JsTopDB(DATABASE_URI)
verification_ids = {}


@Client.on_message(filters.command("start") & filters.incoming)
async def start(client: Client, message):
    await message.react(emoji=random.choice(REACTIONS))
    m = message
    user_id = m.from_user.id
    if len(m.command) == 2 and m.command[1].startswith("notcopy"):
        _, userid, verify_id, file_id = m.command[1].split("_", 3)
        user_id = int(userid)
        grp_id = temp.CHAT.get(user_id, 0)
        settings = await get_settings(grp_id)
        verify_id_info = await db.get_verify_id_info(user_id, verify_id)
        if not verify_id_info or verify_id_info["verified"]:
            await message.reply("<b>ʟɪɴᴋ ᴇxᴘɪʀᴇᴅ ᴛʀʏ ᴀɢᴀɪɴ...</b>")
            return
        ist_timezone = pytz.timezone("Asia/Kolkata")
        if await db.user_verified(user_id):
            key = "third_time_verified"
        else:
            key = (
                "second_time_verified"
                if await db.is_user_verified(user_id)
                else "last_verified"
            )
        current_time = dt.now(tz=ist_timezone)
        result = await db.update_notcopy_user(user_id, {key: current_time})
        await db.update_verify_id_info(user_id, verify_id, {"verified": True})
        if key == "third_time_verified":
            num = 3
        else:
            num = 2 if key == "second_time_verified" else 1
        if key == "third_time_verified":
            msg = script.THIRDT_VERIFY_COMPLETE_TEXT
        else:
            msg = (
                script.SECOND_VERIFY_COMPLETE_TEXT
                if key == "second_time_verified"
                else script.VERIFY_COMPLETE_TEXT
            )
        if message.command[1].startswith("jisshu"):
            verifiedfiles = (
                f"https://telegram.me/{temp.U_NAME}?start=allfiles_{grp_id}_{file_id}"
            )
        else:
            verifiedfiles = (
                f"https://telegram.me/{temp.U_NAME}?start=file_{grp_id}_{file_id}"
            )
        await client.send_message(
            settings["log"],
            script.VERIFIED_LOG_TEXT.format(
                m.from_user.mention,
                user_id,
                dt.now(pytz.timezone("Asia/Kolkata")).strftime("%d %B %Y"),
                num,
            ),
        )
        btn = [
            [
                InlineKeyboardButton("‼️ ᴄʟɪᴄᴋ ʜᴇʀᴇ ᴛᴏ ɢᴇᴛ ꜰɪʟᴇ ‼️", url=verifiedfiles),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(btn)
        await m.reply_photo(
            photo=(VERIFY_IMG),
            caption=msg.format(
                message.from_user.mention, get_readable_time(TWO_VERIFY_GAP)
            ),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML,
        )
        return
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        status = get_status()
        aks = await message.reply_text(f"<b>🔥 ʏᴇs {status},\nʜᴏᴡ ᴄᴀɴ ɪ ʜᴇʟᴘ ʏᴏᴜ??</b>")
        await asyncio.sleep(600)
        await aks.delete()
        await m.delete()
        if not await db.get_chat(message.chat.id):
            total = await client.get_chat_members_count(message.chat.id)
            group_link = await message.chat.export_invite_link()
            user = message.from_user.mention if message.from_user else "Dear"
            await client.send_message(
                LOG_CHANNEL,
                script.NEW_GROUP_TXT.format(
                    temp.B_LINK,
                    message.chat.title,
                    message.chat.id,
                    message.chat.username,
                    group_link,
                    total,
                    user,
                ),
            )
            await db.add_chat(message.chat.id, message.chat.title)
        return
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        await client.send_message(
            LOG_CHANNEL,
            script.NEW_USER_TXT.format(
                temp.B_LINK, message.from_user.id, message.from_user.mention
            ),
        )
    if len(message.command) != 2:
        buttons = [
            [
                InlineKeyboardButton(
                    "⇋ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ ⇋",
                    url=f"http://telegram.dog/{temp.U_NAME}?startgroup=start",
                )
            ],
            [
                InlineKeyboardButton("• ᴅɪꜱᴀʙʟᴇ ᴀᴅꜱ •", callback_data="jisshupremium"),
                InlineKeyboardButton("• ꜱᴘᴇᴄɪᴀʟ •", callback_data="special"),
            ],
            [
                InlineKeyboardButton("• ʜᴇʟᴘ •", callback_data="help"),
                InlineKeyboardButton("• ᴀʙᴏᴜᴛ •", callback_data="about"),
            ],
            [
                InlineKeyboardButton(
                    "• ᴇᴀʀɴ ᴜɴʟɪᴍɪᴛᴇᴅ ᴍᴏɴᴇʏ ᴡɪᴛʜ ʙᴏᴛ •", callback_data="earn"
                )
            ],
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        m = await message.reply_sticker(
            "CAACAgUAAx0CZz_GMwACMBdnXZA4SejgJ6a_0TrNzOfn9ImI_QACNwsAArT4iFVaZPJf8ldVVh4E"
        )
        await asyncio.sleep(1)
        await m.delete()
        await message.reply_photo(
            photo=random.choice(START_IMG),
            caption=script.START_TXT.format(
                message.from_user.mention, get_status(), message.from_user.id
            ),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML,
        )
        return
    if len(message.command) == 2 and message.command[1] in [
        "subscribe",
        "error",
        "okay",
        "help",
    ]:
        buttons = [
            [
                InlineKeyboardButton(
                    "⇋ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ ⇋",
                    url=f"http://telegram.dog/{temp.U_NAME}?startgroup=start",
                )
            ],
            [
                InlineKeyboardButton("• ᴅɪꜱᴀʙʟᴇ ᴀᴅꜱ •", callback_data="jisshupremium"),
                InlineKeyboardButton("• ꜱᴘᴇᴄɪᴀʟ •", callback_data="special"),
            ],
            [
                InlineKeyboardButton("• ʜᴇʟᴘ •", callback_data="help"),
                InlineKeyboardButton("• ᴀʙᴏᴜᴛ •", callback_data="about"),
            ],
            [
                InlineKeyboardButton(
                    "• ᴇᴀʀɴ ᴜɴʟɪᴍɪᴛᴇᴅ ᴍᴏɴᴇʏ ᴡɪᴛʜ ʙᴏᴛ •", callback_data="earn"
                )
            ],
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        return await message.reply_photo(
            photo=START_IMG,
            caption=script.START_TXT.format(
                message.from_user.mention, get_status(), message.from_user.id
            ),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML,
        )
    if len(message.command) == 2 and message.command[1].startswith("reff_"):
        try:
            user_id = int(message.command[1].split("_")[1])
        except ValueError:
            await message.reply_text("𝖨𝗇𝗏𝖺𝗅𝗂𝖽 𝖱𝖾𝖿𝖾𝗋⁉️")
            return
        if user_id == message.from_user.id:
            await message.reply_text("𝖧𝖾𝗒 𝖣𝗎𝖽𝖾 𝖸𝗈𝗎 𝖢𝖺𝗇'𝗍 𝖱𝖾𝖿𝖾𝗋 𝖸𝗈𝗎𝗋𝗌𝖾𝗅𝖿⁉️")
            return
        if referdb.is_user_in_list(message.from_user.id):
            await message.reply_text("‼️ 𝖸𝗈𝗎 𝖧𝖺𝗏𝖾 𝖡𝖾𝖾𝗇 𝖠𝗅𝗅𝗋𝖾𝖺𝖽𝗒 𝖨𝗇𝗏𝗂𝗍𝖾𝖽 𝗈𝗋 𝖩𝗈𝗂𝗇𝖾𝖽")
            return
        if await db.is_user_exist(message.from_user.id):
            await message.reply_text("‼️ 𝖸𝗈𝗎 𝖧𝖺𝗏𝖾 𝖡𝖾𝖾𝗇 𝖠𝗅𝗅𝗋𝖾𝖺𝖽𝗒 𝖨𝗇𝗏𝗂𝗍𝖾𝖽 𝗈𝗋 𝖩𝗈𝗂𝗇𝖾𝖽")
            return
        try:
            uss = await client.get_users(user_id)
        except Exception:
            return
        referdb.add_user(message.from_user.id)
        fromuse = referdb.get_refer_points(user_id) + 10
        if fromuse == 100:
            referdb.add_refer_points(user_id, 0)
            await message.reply_text(f"𝖸𝗈𝗎 𝖧𝖺𝗏𝖾 𝖡𝖾𝖾𝗇 𝖨𝗇𝗏𝗂𝗍𝖾𝖽 𝖡𝗒 {uss.mention}!")
            await client.send_message(
                user_id, text=f"𝖸𝗈𝗎 𝖧𝖺𝗏𝖾 𝖡𝖾𝖾𝗇 𝖨𝗇𝗏𝗂𝗍𝖾𝖽 𝖡𝗒 {message.from_user.mention}!"
            )
            await add_premium(client, user_id, uss)
        else:
            referdb.add_refer_points(user_id, fromuse)
            await message.reply_text(f"𝖸𝗈𝗎 𝖧𝖺𝗏𝖾 𝖡𝖾𝖾𝗇 𝖨𝗇𝗏𝗂𝗍𝖾𝖽 𝖡𝗒 {uss.mention}!")
            await client.send_message(
                user_id, f"𝖸𝗈𝗎 𝖧𝖺𝗏𝖾 𝖨𝗇𝗏𝗂𝗍𝖾𝖽 {message.from_user.mention}!"
            )
        return

    if len(message.command) == 2 and message.command[1].startswith("getfile"):
        searches = message.command[1].split("-", 1)[1]
        search = searches.replace("-", " ")
        message.text = search
        await auto_filter(client, message)
        return

    if len(message.command) == 2 and message.command[1] in ["ads"]:
        msg, _, impression = await mdb.get_advirtisment()
        user = await db.get_user(message.from_user.id)
        seen_ads = user.get("seen_ads", False)
        JISSHU_ADS_LINK = await db.jisshu_get_ads_link()
        buttons = [[InlineKeyboardButton("❌ ᴄʟᴏꜱᴇ ❌", callback_data="close_data")]]
        reply_markup = InlineKeyboardMarkup(buttons)
        if msg:
            await message.reply_photo(
                photo=JISSHU_ADS_LINK if JISSHU_ADS_LINK else URL,
                caption=msg,
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML,
            )
            if impression is not None and not seen_ads:
                await mdb.update_advirtisment_impression(int(impression) - 1)
                await db.update_value(message.from_user.id, "seen_ads", True)
        else:
            await message.reply("<b>No Ads Found</b>")
        await mdb.reset_advertisement_if_expired()
        if msg is None and seen_ads:
            await db.update_value(message.from_user.id, "seen_ads", False)
        return

    data = message.command[1]
    try:
        pre, grp_id, file_id = data.split("_", 2)
        print(f"Group Id - {grp_id}")
    except:
        pre, grp_id, file_id = "", 0, data

    settings = await get_settings(int(data.split("_", 2)[1]))
    if settings.get("fsub_id", AUTH_CHANNEL) == AUTH_REQ_CHANNEL:
        if AUTH_REQ_CHANNEL and not await is_req_subscribed(client, message):
            try:
                invite_link = await client.create_chat_invite_link(
                    int(AUTH_REQ_CHANNEL), creates_join_request=True
                )
            except ChatAdminRequired:
                logger.error("Make sure Bot is admin in Forcesub channel")
                return
            btn = [
                [InlineKeyboardButton("⛔️ ᴊᴏɪɴ ɴᴏᴡ ⛔️", url=invite_link.invite_link)]
            ]
            if message.command[1] != "subscribe":
                btn.append(
                    [
                        InlineKeyboardButton(
                            "♻️ ᴛʀʏ ᴀɢᴀɪɴ ♻️",
                            url=f"https://t.me/{temp.U_NAME}?start={message.command[1]}",
                        )
                    ]
                )
            await client.send_photo(
                chat_id=message.from_user.id,
                photo=FORCESUB_IMG,
                caption=script.FORCESUB_TEXT,
                reply_markup=InlineKeyboardMarkup(btn),
                parse_mode=enums.ParseMode.HTML,
            )
            return
    else:
        id = settings.get("fsub_id", AUTH_CHANNEL)
        channel = int(id)
        btn = []
        if channel != AUTH_CHANNEL and not await is_subscribed(
            client, message.from_user.id, channel
        ):
            invite_link_custom = await client.create_chat_invite_link(channel)
            btn.append(
                [
                    InlineKeyboardButton(
                        "⛔️ ᴊᴏɪɴ ɴᴏᴡ ⛔️", url=invite_link_custom.invite_link
                    )
                ]
            )
        if not await is_req_subscribed(client, message):
            invite_link_default = await client.create_chat_invite_link(
                int(AUTH_CHANNEL), creates_join_request=True
            )
            btn.append(
                [
                    InlineKeyboardButton(
                        "⛔️ ᴊᴏɪɴ ɴᴏᴡ ⛔️", url=invite_link_default.invite_link
                    )
                ]
            )
        if message.command[1] != "subscribe" and (
            await is_req_subscribed(client, message) is False
            or await is_subscribed(client, message.from_user.id, channel) is False
        ):
            btn.append(
                [
                    InlineKeyboardButton(
                        "♻️ ᴛʀʏ ᴀɢᴀɪɴ ♻️",
                        url=f"https://t.me/{temp.U_NAME}?start={message.command[1]}",
                    )
                ]
            )
        if btn:
            await client.send_photo(
                chat_id=message.from_user.id,
                photo=FORCESUB_IMG,
                caption=script.FORCESUB_TEXT,
                reply_markup=InlineKeyboardMarkup(btn),
                parse_mode=enums.ParseMode.HTML,
            )
            return

    user_id = m.from_user.id
    if not await db.has_premium_access(user_id):
        grp_id = int(grp_id)
        print(f"Group Id - {grp_id}")
        user_verified = await db.is_user_verified(user_id)
        settings = await get_settings(grp_id)
        print(f"Id Settings - {settings}")
        is_second_shortener = await db.use_second_shortener(
            user_id, settings.get("verify_time", TWO_VERIFY_GAP)
        )
        is_third_shortener = await db.use_third_shortener(
            user_id, settings.get("third_verify_time", THREE_VERIFY_GAP)
        )
        if (
            settings.get("is_verify", IS_VERIFY)
            and not user_verified
            or is_second_shortener
            or is_third_shortener
        ):
            verify_id = "".join(
                random.choices(string.ascii_uppercase + string.digits, k=7)
            )
            await db.create_verify_id(user_id, verify_id)
            temp.CHAT[user_id] = grp_id
            if message.command[1].startswith("allfiles"):
                verify = await get_shortlink(
                    f"https://telegram.me/{temp.U_NAME}?start=jisshu_{user_id}_{verify_id}_{file_id}",
                    grp_id,
                    is_second_shortener,
                    is_third_shortener,
                )
            else:
                verify = await get_shortlink(
                    f"https://telegram.me/{temp.U_NAME}?start=notcopy_{user_id}_{verify_id}_{file_id}",
                    grp_id,
                    is_second_shortener,
                    is_third_shortener,
                )
            if is_third_shortener:
                howtodownload = settings.get("tutorial_3", TUTORIAL_3)
            else:
                howtodownload = (
                    settings.get("tutorial_2", TUTORIAL_2)
                    if is_second_shortener
                    else settings.get("tutorial", TUTORIAL)
                )
            buttons = [
                [
                    InlineKeyboardButton(text="✅ ᴠᴇʀɪꜰʏ ✅", url=verify),
                    InlineKeyboardButton(text="ʜᴏᴡ ᴛᴏ ᴠᴇʀɪꜰʏ❓", url=howtodownload),
                ],
                [
                    InlineKeyboardButton(
                        text="😁 ʙᴜʏ sᴜʙsᴄʀɪᴘᴛɪᴏɴ - ɴᴏ ɴᴇᴇᴅ ᴛᴏ ᴠᴇʀɪғʏ 😁",
                        callback_data="getpremium",
                    ),
                ],
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            if await db.user_verified(user_id):
                msg = script.THIRDT_VERIFICATION_TEXT
            else:
                msg = (
                    script.SECOND_VERIFICATION_TEXT
                    if is_second_shortener
                    else script.VERIFICATION_TEXT
                )
            d = await m.reply_text(
                text=msg.format(message.from_user.mention, get_status()),
                protect_content=True,
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML,
            )
            await asyncio.sleep(300)
            await d.delete()
            await m.delete()
            return

    if data and data.startswith("allfiles"):
        _, grp_id, key = data.split("_", 2)
        files = temp.FILES_ID.get(key)
        if not files:
            await message.reply_text("<b>⚠️ ᴀʟʟ ꜰɪʟᴇs ɴᴏᴛ ꜰᴏᴜɴᴅ ⚠️</b>")
            return
        files_to_delete = []
        for file in files:
            user_id = message.from_user.id
            grp_id = temp.CHAT.get(user_id)
            settings = await get_settings(grp_id)
            CAPTION = settings["caption"]
            f_caption = CAPTION.format(
                file_name=formate_file_name(file.file_name),
                file_size=get_size(file.file_size),
                file_caption=file.caption,
            )
            btn = [
                [
                    InlineKeyboardButton(
                        "✛ ᴡᴀᴛᴄʜ & ᴅᴏᴡɴʟᴏᴀᴅ ✛", callback_data=f"stream#{file.file_id}"
                    )
                ]
            ]
            toDel = await client.send_cached_media(
                chat_id=message.from_user.id,
                file_id=file.file_id,
                caption=f_caption,
                reply_markup=InlineKeyboardMarkup(btn),
            )
            files_to_delete.append(toDel)

        delCap = "<i>ᴀʟʟ {} ꜰɪʟᴇꜱ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ᴀꜰᴛᴇʀ {} ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ᴠɪᴏʟᴀᴛɪᴏɴs!</i>".format(
            len(files_to_delete),
            (
                f"{FILE_AUTO_DEL_TIMER / 60} ᴍɪɴᴜᴛᴇs"
                if FILE_AUTO_DEL_TIMER >= 60
                else f"{FILE_AUTO_DEL_TIMER} sᴇᴄᴏɴᴅs"
            ),
        )
        afterDelCap = "<i>ᴀʟʟ {} ꜰɪʟᴇꜱ ᴀʀᴇ ᴅᴇʟᴇᴛᴇᴅ ᴀꜰᴛᴇʀ {} ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ᴠɪᴏʟᴀᴛɪᴏɴs!</i>".format(
            len(files_to_delete),
            (
                f"{FILE_AUTO_DEL_TIMER / 60} ᴍɪɴᴜᴛᴇs"
                if FILE_AUTO_DEL_TIMER >= 60
                else f"{FILE_AUTO_DEL_TIMER} sᴇᴄᴏɴᴅs"
            ),
        )
        replyed = await message.reply(delCap)
        await asyncio.sleep(FILE_AUTO_DEL_TIMER)
        for file in files_to_delete:
            try:
                await file.delete()
            except:
                pass
        return await replyed.edit(
            afterDelCap,
        )
    if not data:
        return

    files_ = await get_file_details(file_id)
    if not files_:
        pre, file_id = (
            (base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))).decode("ascii")
        ).split("_", 1)
        return await message.reply("<b>⚠️ ᴀʟʟ ꜰɪʟᴇs ɴᴏᴛ ꜰᴏᴜɴᴅ ⚠️</b>")
    files = files_[0]
    settings = await get_settings(grp_id)
    CAPTION = settings["caption"]
    f_caption = CAPTION.format(
        file_name=formate_file_name(files.file_name),
        file_size=get_size(files.file_size),
        file_caption=files.caption,
    )
    btn = [
        [
            InlineKeyboardButton(
                "✛ ᴡᴀᴛᴄʜ & ᴅᴏᴡɴʟᴏᴀᴅ ✛", callback_data=f"stream#{file_id}"
            )
        ]
    ]
    toDel = await client.send_cached_media(
        chat_id=message.from_user.id,
        file_id=file_id,
        caption=f_caption,
        reply_markup=InlineKeyboardMarkup(btn),
    )
    delCap = "<i>ʏᴏᴜʀ ꜰɪʟᴇ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ᴀғᴛᴇʀ {} ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ᴠɪᴏʟᴀᴛɪᴏɴs!</i>".format(
        f"{FILE_AUTO_DEL_TIMER / 60} ᴍɪɴᴜᴛᴇs"
        if FILE_AUTO_DEL_TIMER >= 60
        else f"{FILE_AUTO_DEL_TIMER} sᴇᴄᴏɴᴅs"
    )
    afterDelCap = (
        "<i>ʏᴏᴜʀ ꜰɪʟᴇ ɪs ᴅᴇʟᴇᴛᴇᴅ ᴀғᴛᴇʀ {} ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ᴠɪᴏʟᴀᴛɪᴏɴs!</i>".format(
            f"{FILE_AUTO_DEL_TIMER / 60} ᴍɪɴᴜᴛᴇs"
            if FILE_AUTO_DEL_TIMER >= 60
            else f"{FILE_AUTO_DEL_TIMER} sᴇᴄᴏɴᴅs"
        )
    )
    replyed = await message.reply(delCap, reply_to_message_id=toDel.id)
    await asyncio.sleep(FILE_AUTO_DEL_TIMER)
    await toDel.delete()
    return await replyed.edit(afterDelCap)


@Client.on_message(filters.command("delete"))
async def delete(bot, message):
    if message.from_user.id not in ADMINS:
        await message.reply("ᴏɴʟʏ ᴛʜᴇ ʙᴏᴛ ᴏᴡɴᴇʀ ᴄᴀɴ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ... 😑")
        return
    """Delete file from database"""
    reply = message.reply_to_message
    if reply and reply.media:
        msg = await message.reply("ᴘʀᴏᴄᴇssɪɴɢ...⏳", quote=True)
    else:
        await message.reply(
            "Reply to file with /delete which you want to delete", quote=True
        )
        return
    for file_type in ("document", "video", "audio"):
        media = getattr(reply, file_type, None)
        if media is not None:
            break
    else:
        await msg.edit("<b>ᴛʜɪs ɪs ɴᴏᴛ sᴜᴘᴘᴏʀᴛᴇᴅ ꜰɪʟᴇ ꜰᴏʀᴍᴀᴛ</b>")
        return

    file_id, file_ref = unpack_new_file_id(media.file_id)
    result = await Media.collection.delete_one(
        {
            "_id": file_id,
        }
    )
    if result.deleted_count:
        await msg.edit("<b>ꜰɪʟᴇ ɪs sᴜᴄᴄᴇssꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ꜰʀᴏᴍ ᴅᴀᴛᴀʙᴀsᴇ 💥</b>")
    else:
        file_name = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name))
        result = await Media.collection.delete_many(
            {
                "file_name": file_name,
                "file_size": media.file_size,
                "mime_type": media.mime_type,
            }
        )
        if result.deleted_count:
            await msg.edit("<b>ꜰɪʟᴇ ɪs sᴜᴄᴄᴇssꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ꜰʀᴏᴍ ᴅᴀᴛᴀʙᴀsᴇ 💥</b>")
        else:
            result = await Media.collection.delete_many(
                {
                    "file_name": media.file_name,
                    "file_size": media.file_size,
                    "mime_type": media.mime_type,
                }
            )
            if result.deleted_count:
                await msg.edit("<b>ꜰɪʟᴇ ɪs sᴜᴄᴄᴇssꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ꜰʀᴏᴍ ᴅᴀᴛᴀʙᴀsᴇ 💥</b>")
            else:
                await msg.edit("<b>ꜰɪʟᴇ ɴᴏᴛ ꜰᴏᴜɴᴅ ɪɴ ᴅᴀᴛᴀʙᴀsᴇ</b>")


@Client.on_message(filters.command("deleteall"))
async def delete_all_index(bot, message):
    files = await Media.count_documents()
    if int(files) == 0:
        return await message.reply_text("Not have files to delete")
    btn = [
        [InlineKeyboardButton(text="ʏᴇs", callback_data="all_files_delete")],
        [InlineKeyboardButton(text="ᴄᴀɴᴄᴇʟ", callback_data="close_data")],
    ]
    if message.from_user.id not in ADMINS:
        await message.reply("ᴏɴʟʏ ᴛʜᴇ ʙᴏᴛ ᴏᴡɴᴇʀ ᴄᴀɴ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ... 😑")
        return
    await message.reply_text(
        "<b>ᴛʜɪs ᴡɪʟʟ ᴅᴇʟᴇᴛᴇ ᴀʟʟ ɪɴᴅᴇxᴇᴅ ꜰɪʟᴇs.\nᴅᴏ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ??</b>",
        reply_markup=InlineKeyboardMarkup(btn),
    )


@Client.on_message(filters.command("settings"))
async def settings(client, message):
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return await message.reply(
            "<b>💔 ʏᴏᴜ ᴀʀᴇ ᴀɴᴏɴʏᴍᴏᴜꜱ ᴀᴅᴍɪɴ ʏᴏᴜ ᴄᴀɴ'ᴛ ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ...</b>"
        )
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<code>ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ.</code>")
    grp_id = message.chat.id
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text("<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>")
    settings = await get_settings(grp_id)
    title = message.chat.title
    if settings is not None:
        buttons = [
            [
                InlineKeyboardButton(
                    "ᴀᴜᴛᴏ ꜰɪʟᴛᴇʀ",
                    callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    "ᴏɴ ✓" if settings["auto_filter"] else "ᴏғғ ✗",
                    callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    "ɪᴍᴅʙ", callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}'
                ),
                InlineKeyboardButton(
                    "ᴏɴ ✓" if settings["imdb"] else "ᴏғғ ✗",
                    callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    "sᴘᴇʟʟ ᴄʜᴇᴄᴋ",
                    callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    "ᴏɴ ✓" if settings["spell_check"] else "ᴏғғ ✗",
                    callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    "ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ",
                    callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    (
                        f"{get_readable_time(DELETE_TIME)}"
                        if settings["auto_delete"]
                        else "ᴏғғ ✗"
                    ),
                    callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    "ʀᴇsᴜʟᴛ ᴍᴏᴅᴇ",
                    callback_data=f'setgs#link#{settings["link"]}#{str(grp_id)}',
                ),
                InlineKeyboardButton(
                    "⛓ ʟɪɴᴋ" if settings["link"] else "🧲 ʙᴜᴛᴛᴏɴ",
                    callback_data=f'setgs#link#{settings["link"]}#{str(grp_id)}',
                ),
            ],
            [InlineKeyboardButton("❌ ᴄʟᴏsᴇ ❌", callback_data="close_data")],
        ]
        await message.reply_text(
            text=f"ᴄʜᴀɴɢᴇ ʏᴏᴜʀ sᴇᴛᴛɪɴɢs ꜰᴏʀ <b>'{title}'</b> ᴀs ʏᴏᴜʀ ᴡɪsʜ ✨",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=enums.ParseMode.HTML,
        )
    else:
        await message.reply_text("<b>ꜱᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ</b>")


@Client.on_message(filters.command("set_template"))
async def save_template(client, message):
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")
    grp_id = message.chat.id
    title = message.chat.title
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text("<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>")
    try:
        template = message.text.split(" ", 1)[1]
    except:
        return await message.reply_text("Command Incomplete!")
    await save_group_settings(grp_id, "template", template)
    await message.reply_text(
        f"Successfully changed template for {title} to\n\n{template}",
        disable_web_page_preview=True,
    )


@Client.on_message(filters.command("send"))
async def send_msg(bot, message):
    if message.from_user.id not in ADMINS:
        await message.reply("<b>ᴏɴʟʏ ᴛʜᴇ ʙᴏᴛ ᴏᴡɴᴇʀ ᴄᴀɴ ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ...</b>")
        return
    if message.reply_to_message:
        target_ids = message.text.split(" ")[1:]
        if not target_ids:
            await message.reply_text(
                "<b>ᴘʟᴇᴀꜱᴇ ᴘʀᴏᴠɪᴅᴇ ᴏɴᴇ ᴏʀ ᴍᴏʀᴇ ᴜꜱᴇʀ ɪᴅꜱ ᴀꜱ ᴀ ꜱᴘᴀᴄᴇ...</b>"
            )
            return
        out = "\n\n"
        success_count = 0
        try:
            users = await db.get_all_users()
            for target_id in target_ids:
                try:
                    user = await bot.get_users(target_id)
                    out += f"{user.id}\n"
                    await message.reply_to_message.copy(int(user.id))
                    success_count += 1
                except Exception as e:
                    out += f"‼️ ᴇʀʀᴏʀ ɪɴ ᴛʜɪꜱ ɪᴅ - <code>{target_id}</code> <code>{str(e)}</code>\n"
            await message.reply_text(
                f"<b>✅️ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴍᴇꜱꜱᴀɢᴇ ꜱᴇɴᴛ ɪɴ `{success_count}` ɪᴅ\n<code>{out}</code></b>"
            )
        except Exception as e:
            await message.reply_text(f"<b>‼️ ᴇʀʀᴏʀ - <code>{e}</code></b>")
    else:
        await message.reply_text(
            "<b>ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ᴀꜱ ᴀ ʀᴇᴘʟʏ ᴛᴏ ᴀɴʏ ᴍᴇꜱꜱᴀɢᴇ, ꜰᴏʀ ᴇɢ - <code>/send userid1 userid2</code></b>"
        )


@Client.on_message(filters.regex("#request"))
async def send_request(bot, message):
    try:
        request = message.text.split(" ", 1)[1]
    except:
        await message.reply_text("<b>‼️ ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ɪɴᴄᴏᴍᴘʟᴇᴛᴇ</b>")
        return
    buttons = [
        [InlineKeyboardButton("👀 ᴠɪᴇᴡ ʀᴇǫᴜᴇꜱᴛ 👀", url=f"{message.link}")],
        [
            InlineKeyboardButton(
                "⚙ sʜᴏᴡ ᴏᴘᴛɪᴏɴ ⚙",
                callback_data=f"show_options#{message.from_user.id}#{message.id}",
            )
        ],
    ]
    sent_request = await bot.send_message(
        REQUEST_CHANNEL,
        script.REQUEST_TXT.format(
            message.from_user.mention, message.from_user.id, request
        ),
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    btn = [
        [InlineKeyboardButton("✨ ᴠɪᴇᴡ ʏᴏᴜʀ ʀᴇǫᴜᴇꜱᴛ ✨", url=f"{sent_request.link}")]
    ]
    await message.reply_text(
        "<b>✅ sᴜᴄᴄᴇꜱꜱғᴜʟʟʏ ʏᴏᴜʀ ʀᴇǫᴜᴇꜱᴛ ʜᴀꜱ ʙᴇᴇɴ ᴀᴅᴅᴇᴅ, ᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ ꜱᴏᴍᴇᴛɪᴍᴇ...</b>",
        reply_markup=InlineKeyboardMarkup(btn),
    )


@Client.on_message(filters.command("search"))
async def search_files(bot, message):
    if message.from_user.id not in ADMINS:
        await message.reply("Only the bot owner can use this command... 😑")
        return
    chat_type = message.chat.type
    if chat_type != enums.ChatType.PRIVATE:
        return await message.reply_text(
            f"<b>Hey {message.from_user.mention}, this command won't work in groups. It only works in my PM!</b>"
        )
    try:
        keyword = message.text.split(" ", 1)[1]
    except IndexError:
        return await message.reply_text(
            f"<b>Hey {message.from_user.mention}, give me a keyword along with the command to delete files.</b>"
        )
    files, total = await get_bad_files(keyword)
    if int(total) == 0:
        await message.reply_text(
            "<i>I could not find any files with this keyword 😐</i>"
        )
        return
    file_names = "\n\n".join(
        f"{index + 1}. {item['file_name']}" for index, item in enumerate(files)
    )
    file_data = f"🚫 Your search - '{keyword}':\n\n{file_names}"
    with open("file_names.txt", "w", encoding="utf-8") as file:
        file.write(file_data)
    await message.reply_document(
        document="file_names.txt",
        caption=f"<b>♻️ ʙʏ ʏᴏᴜʀ ꜱᴇᴀʀᴄʜ, ɪ ꜰᴏᴜɴᴅ - <code>{total}</code> ꜰɪʟᴇs</b>",
        parse_mode=enums.ParseMode.HTML,
    )
    os.remove("file_names.txt")


@Client.on_message(filters.command("deletefiles"))
async def deletemultiplefiles(bot, message):
    if message.from_user.id not in ADMINS:
        await message.reply("ᴏɴʟʏ ᴛʜᴇ ʙᴏᴛ ᴏᴡɴᴇʀ ᴄᴀɴ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ... 😑")
        return
    chat_type = message.chat.type
    if chat_type != enums.ChatType.PRIVATE:
        return await message.reply_text(
            f"<b>ʜᴇʏ {message.from_user.mention}, ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ᴡᴏɴ'ᴛ ᴡᴏʀᴋ ɪɴ ɢʀᴏᴜᴘs. ɪᴛ ᴏɴʟʏ ᴡᴏʀᴋs ᴏɴ ᴍʏ ᴘᴍ !!</b>"
        )
    else:
        pass
    try:
        keyword = message.text.split(" ", 1)[1]
    except:
        return await message.reply_text(
            f"<b>ʜᴇʏ {message.from_user.mention}, ɢɪᴠᴇ ᴍᴇ ᴀ ᴋᴇʏᴡᴏʀᴅ ᴀʟᴏɴɢ ᴡɪᴛʜ ᴛʜᴇ ᴄᴏᴍᴍᴀɴᴅ ᴛᴏ ᴅᴇʟᴇᴛᴇ ꜰɪʟᴇs.</b>"
        )
    files, total = await get_bad_files(keyword)
    if int(total) == 0:
        await message.reply_text(
            "<i>ɪ ᴄᴏᴜʟᴅ ɴᴏᴛ ꜰɪɴᴅ ᴀɴʏ ꜰɪʟᴇs ᴡɪᴛʜ ᴛʜɪs ᴋᴇʏᴡᴏʀᴅ 😐</i>"
        )
        return
    btn = [
        [
            InlineKeyboardButton(
                "ʏᴇs, ᴄᴏɴᴛɪɴᴜᴇ ✅", callback_data=f"killfilesak#{keyword}"
            )
        ],
        [InlineKeyboardButton("ɴᴏ, ᴀʙᴏʀᴛ ᴏᴘᴇʀᴀᴛɪᴏɴ 😢", callback_data="close_data")],
    ]
    await message.reply_text(
        text=f"<b>ᴛᴏᴛᴀʟ ꜰɪʟᴇs ꜰᴏᴜɴᴅ - <code>{total}</code>\n\nᴅᴏ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ?\n\nɴᴏᴛᴇ:- ᴛʜɪs ᴄᴏᴜʟᴅ ʙᴇ ᴀ ᴅᴇsᴛʀᴜᴄᴛɪᴠᴇ ᴀᴄᴛɪᴏɴ!!</b>",
        reply_markup=InlineKeyboardMarkup(btn),
        parse_mode=enums.ParseMode.HTML,
    )


@Client.on_message(filters.command("del_file"))
async def delete_files(bot, message):
    if message.from_user.id not in ADMINS:
        await message.reply("Only the bot owner can use this command... 😑")
        return
    chat_type = message.chat.type
    if chat_type != enums.ChatType.PRIVATE:
        return await message.reply_text(
            f"<b>Hey {message.from_user.mention}, this command won't work in groups. It only works on my PM!</b>"
        )
    try:
        keywords = message.text.split(" ", 1)[1].split(",")
    except IndexError:
        return await message.reply_text(
            f"<b>Hey {message.from_user.mention}, give me keywords separated by commas along with the command to delete files.</b>"
        )
    deleted_files_count = 0
    not_found_files = []
    for keyword in keywords:
        result = await Media.collection.delete_many({"file_name": keyword.strip()})
        if result.deleted_count:
            deleted_files_count += 1
        else:
            not_found_files.append(keyword.strip())
    if deleted_files_count > 0:
        await message.reply_text(
            f"<b>{deleted_files_count} file successfully deleted from the database 💥</b>"
        )
    if not_found_files:
        await message.reply_text(
            f'<b>Files not found in the database - <code>{", ".join(not_found_files)}</code></b>'
        )


@Client.on_message(filters.command("set_caption"))
async def save_caption(client, message):
    grp_id = message.chat.id
    title = message.chat.title
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text("<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>")
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")
    try:
        caption = message.text.split(" ", 1)[1]
    except:
        return await message.reply_text("Command Incomplete!")
    await save_group_settings(grp_id, "caption", caption)
    await message.reply_text(
        f"Successfully changed caption for {title} to\n\n{caption}",
        disable_web_page_preview=True,
    )


@Client.on_message(filters.command("set_tutorial"))
async def save_tutorial(client, message):
    grp_id = message.chat.id
    title = message.chat.title
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text("<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>")
    try:
        tutorial = message.text.split(" ", 1)[1]
    except:
        return await message.reply_text(
            "<b>Command Incomplete!!\n\nuse like this -</b>\n\n<code>/set_caption https://telegram.me/+JWsoDEJEB9EyNDU1</code>"
        )
    await save_group_settings(grp_id, "tutorial", tutorial)
    await message.reply_text(
        f"<b>Successfully Changed 1st Verification Tutorial For {title} To</b>\n\n{tutorial}",
        disable_web_page_preview=True,
    )


@Client.on_message(filters.command("set_tutorial_2"))
async def set_tutorial_2(client, message):
    grp_id = message.chat.id
    title = message.chat.title
    invite_link = await client.export_chat_invite_link(grp_id)
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text("<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>")
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text(
            f"<b>ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...\n\nGroup Name: {title}\nGroup ID: {grp_id}\nGroup Invite Link: {invite_link}</b>"
        )
    try:
        tutorial = message.text.split(" ", 1)[1]
    except:
        return await message.reply_text(
            "<b>ᴄᴏᴍᴍᴀɴᴅ ɪɴᴄᴏᴍᴘʟᴇᴛᴇ !!\n\nᴜꜱᴇ ʟɪᴋᴇ ᴛʜɪꜱ -</b>\n\n<code>/set_tutorial_2 https://telegram.dog/DwldMS/2</code>"
        )
    await save_group_settings(grp_id, "tutorial_2", tutorial)
    await message.reply_text(
        f"<b>Successfully Changed 2nd Verification Tutorial For {title} To</b>\n\n{tutorial}",
        disable_web_page_preview=True,
    )


@Client.on_message(filters.command("set_tutorial_3"))
async def set_tutorial_3(client, message):
    grp_id = message.chat.id
    title = message.chat.title
    invite_link = await client.export_chat_invite_link(grp_id)
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text("<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>")
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text(
            f"<b>ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...\n\nGroup Name: {title}\nGroup ID: {grp_id}\nGroup Invite Link: {invite_link}</b>"
        )
    try:
        tutorial = message.text.split(" ", 1)[1]
    except:
        return await message.reply_text(
            "<b>Command Incomplete!!\n\nuse like this -</b>\n\n<code>/set_tutorial https://telegram.dog/infinity_botzz</code>"
        )
    await save_group_settings(grp_id, "tutorial_3", tutorial)
    await message.reply_text(
        f"<b>Successfully Changed 3rd Verification Tutorial For {title} To</b>\n\n{tutorial}",
        disable_web_page_preview=True,
    )


@Client.on_message(filters.command("set_verify"))
async def set_shortner(c, m):
    grp_id = m.chat.id
    chat_type = m.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await m.reply_text("<b>ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")
    if not await is_check_admin(c, grp_id, m.from_user.id):
        return await m.reply_text("<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>")
    if len(m.text.split()) == 1:
        await m.reply(
            "<b>Use this command like this - \n\n`/set_shortner tnshort.net 9bccb0b14ed6841652fa22d3481907788c1b8838`</b>"
        )
        return
    sts = await m.reply("<b>♻️ ᴄʜᴇᴄᴋɪɴɢ...</b>")
    await asyncio.sleep(1.2)
    await sts.delete()
    try:
        URL = m.command[1]
        API = m.command[2]
        resp = requests.get(
            f"https://{URL}/api?api={API}&url=https://t.me/+BJfqwUjbkQFmNTU1"
        ).json()
        if resp["status"] == "success":
            SHORT_LINK = resp["shortenedUrl"]
        await save_group_settings(grp_id, "shortner", URL)
        await save_group_settings(grp_id, "api", API)
        await m.reply_text(
            f"<b><u>✓ sᴜᴄᴄᴇssꜰᴜʟʟʏ ʏᴏᴜʀ sʜᴏʀᴛɴᴇʀ ɪs ᴀᴅᴅᴇᴅ</u>\n\nᴅᴇᴍᴏ - {SHORT_LINK}\n\nsɪᴛᴇ - `{URL}`\n\nᴀᴘɪ - `{API}`</b>",
            quote=True,
        )
        user_id = m.from_user.id
        user_info = (
            f"@{m.from_user.username}"
            if m.from_user.username
            else f"{m.from_user.mention}"
        )
        link = (await c.get_chat(m.chat.id)).invite_link
        grp_link = f"[{m.chat.title}]({link})"
        log_message = f"#New_Shortner_Set_For_1st_Verify\n\nName - {user_info}\nId - `{user_id}`\n\nDomain name - {URL}\nApi - `{API}`\nGroup link - {grp_link}"
        await c.send_message(
            LOG_API_CHANNEL, log_message, disable_web_page_preview=True
        )
    except Exception as e:
        await save_group_settings(grp_id, "shortner", SHORTENER_WEBSITE)
        await save_group_settings(grp_id, "api", SHORTENER_API)
        await m.reply_text(
            f"<b><u>💢 ᴇʀʀᴏʀ ᴏᴄᴄᴏᴜʀᴇᴅ!!</u>\n\nᴀᴜᴛᴏ ᴀᴅᴅᴇᴅ ʙᴏᴛ ᴏᴡɴᴇʀ ᴅᴇꜰᴜʟᴛ sʜᴏʀᴛɴᴇʀ\n\nɪꜰ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴄʜᴀɴɢᴇ ᴛʜᴇɴ ᴜsᴇ ᴄᴏʀʀᴇᴄᴛ ꜰᴏʀᴍᴀᴛ ᴏʀ ᴀᴅᴅ ᴠᴀʟɪᴅ sʜᴏʀᴛʟɪɴᴋ ᴅᴏᴍᴀɪɴ ɴᴀᴍᴇ & ᴀᴘɪ\n\nʏᴏᴜ ᴄᴀɴ ᴀʟsᴏ ᴄᴏɴᴛᴀᴄᴛ ᴏᴜʀ <a href=https://telegram.me/+JWsoDEJEB9EyNDU1>sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ</a> ꜰᴏʀ sᴏʟᴠᴇ ᴛʜɪs ɪssᴜᴇ...\n\nʟɪᴋᴇ -\n\n`/set_shortner mdiskshortner.link e7beb3c8f756dfa15d0bec495abc65f58c0dfa95`\n\n💔 ᴇʀʀᴏʀ - <code>{e}</code></b>",
            quote=True,
        )


@Client.on_message(filters.command("set_verify_2"))
async def set_shortner_2(c, m):
    grp_id = m.chat.id
    chat_type = m.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await m.reply_text("<b>ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")
    if not await is_check_admin(c, grp_id, m.from_user.id):
        return await m.reply_text("<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>")
    if len(m.text.split()) == 1:
        await m.reply(
            "<b>Use this command like this - \n\n`/set_shortner_2 tnshort.net 9bccb0b14ed6841652fa22d3481907788c1b8838`</b>"
        )
        return
    sts = await m.reply("<b>♻️ ᴄʜᴇᴄᴋɪɴɢ...</b>")
    await asyncio.sleep(1.2)
    await sts.delete()
    try:
        URL = m.command[1]
        API = m.command[2]
        resp = requests.get(
            f"https://{URL}/api?api={API}&url=https://t.me/+BJfqwUjbkQFmNTU1"
        ).json()
        if resp["status"] == "success":
            SHORT_LINK = resp["shortenedUrl"]
        await save_group_settings(grp_id, "shortner_two", URL)
        await save_group_settings(grp_id, "api_two", API)
        await m.reply_text(
            f"<b><u>✅ sᴜᴄᴄᴇssꜰᴜʟʟʏ ʏᴏᴜʀ sʜᴏʀᴛɴᴇʀ ɪs ᴀᴅᴅᴇᴅ</u>\n\nᴅᴇᴍᴏ - {SHORT_LINK}\n\nsɪᴛᴇ - `{URL}`\n\nᴀᴘɪ - `{API}`</b>",
            quote=True,
        )
        user_id = m.from_user.id
        user_info = (
            f"@{m.from_user.username}"
            if m.from_user.username
            else f"{m.from_user.mention}"
        )
        link = (await c.get_chat(m.chat.id)).invite_link
        grp_link = f"[{m.chat.title}]({link})"
        log_message = f"#New_Shortner_Set_For_2nd_Verify\n\nName - {user_info}\nId - `{user_id}`\n\nDomain name - {URL}\nApi - `{API}`\nGroup link - {grp_link}"
        await c.send_message(
            LOG_API_CHANNEL, log_message, disable_web_page_preview=True
        )
    except Exception as e:
        await save_group_settings(grp_id, "shortner_two", SHORTENER_WEBSITE2)
        await save_group_settings(grp_id, "api_two", SHORTENER_API2)
        await m.reply_text(
            f"<b><u>💢 ᴇʀʀᴏʀ ᴏᴄᴄᴏᴜʀᴇᴅ!!</u>\n\nᴀᴜᴛᴏ ᴀᴅᴅᴇᴅ ʙᴏᴛ ᴏᴡɴᴇʀ ᴅᴇꜰᴜʟᴛ sʜᴏʀᴛɴᴇʀ\n\nɪꜰ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴄʜᴀɴɢᴇ ᴛʜᴇɴ ᴜsᴇ ᴄᴏʀʀᴇᴄᴛ ꜰᴏʀᴍᴀᴛ ᴏʀ ᴀᴅᴅ ᴠᴀʟɪᴅ sʜᴏʀᴛʟɪɴᴋ ᴅᴏᴍᴀɪɴ ɴᴀᴍᴇ & ᴀᴘɪ\n\nʏᴏᴜ ᴄᴀɴ ᴀʟsᴏ ᴄᴏɴᴛᴀᴄᴛ ᴏᴜʀ <a href=https://telegram.me/+JWsoDEJEB9EyNDU1>sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ</a> ꜰᴏʀ sᴏʟᴠᴇ ᴛʜɪs ɪssᴜᴇ...\n\nʟɪᴋᴇ -\n\n`/set_shortner_2 mdiskshortner.link e7beb3c8f756dfa15d0bec495abc65f58c0dfa95`\n\n💔 ᴇʀʀᴏʀ - <code>{e}</code></b>",
            quote=True,
        )


@Client.on_message(filters.command("set_verify_3"))
async def set_shortner_3(c, m):
    chat_type = m.chat.type
    if chat_type == enums.ChatType.PRIVATE:
        return await m.reply_text(
            "<b>Use this command in Your group ! Not in Private</b>"
        )
    if len(m.text.split()) == 1:
        return await m.reply(
            "<b>Use this command like this - \n\n`/set_shortner_3 tnshort.net 9bccb0b14ed6841652fa22d3481907788c1b8838`</b>"
        )
    sts = await m.reply("<b>♻️ ᴄʜᴇᴄᴋɪɴɢ...</b>")
    await sts.delete()
    userid = m.from_user.id if m.from_user else None
    if not userid:
        return await m.reply("<b>⚠️ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ᴏꜰ ᴛʜɪs ɢʀᴏᴜᴘ</b>")
    grp_id = m.chat.id
    # check if user admin or not
    if not await is_check_admin(c, grp_id, userid):
        return await m.reply_text("<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>")
    if len(m.command) == 1:
        await m.reply_text(
            "<b>ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ᴛᴏ ᴀᴅᴅ sʜᴏʀᴛɴᴇʀ & ᴀᴘɪ\n\nᴇx - `/set_shortner_3 mdiskshortner.link e7beb3c8f756dfa15d0bec495abc65f58c0dfa95`</b>",
            quote=True,
        )
        return
    try:
        URL = m.command[1]
        API = m.command[2]
        resp = requests.get(
            f"https://{URL}/api?api={API}&url=https://t.me/+BJfqwUjbkQFmNTU1"
        ).json()
        if resp["status"] == "success":
            SHORT_LINK = resp["shortenedUrl"]
        await save_group_settings(grp_id, "shortner_three", URL)
        await save_group_settings(grp_id, "api_three", API)
        await m.reply_text(
            f"<b><u>✅ sᴜᴄᴄᴇssꜰᴜʟʟʏ ʏᴏᴜʀ sʜᴏʀᴛɴᴇʀ ɪs ᴀᴅᴅᴇᴅ</u>\n\nᴅᴇᴍᴏ - {SHORT_LINK}\n\nsɪᴛᴇ - `{URL}`\n\nᴀᴘɪ - `{API}`</b>",
            quote=True,
        )
        user_id = m.from_user.id
        if m.from_user.username:
            user_info = f"@{m.from_user.username}"
        else:
            user_info = f"{m.from_user.mention}"
        link = (await c.get_chat(m.chat.id)).invite_link
        grp_link = f"[{m.chat.title}]({link})"
        log_message = f"#New_Shortner_Set_For_3rd_Verify\n\nName - {user_info}\nId - `{user_id}`\n\nDomain name - {URL}\nApi - `{API}`\nGroup link - {grp_link}"
        await c.send_message(
            LOG_API_CHANNEL, log_message, disable_web_page_preview=True
        )
    except Exception as e:
        await save_group_settings(grp_id, "shortner_three", SHORTENER_WEBSITE3)
        await save_group_settings(grp_id, "api_three", SHORTENER_API3)
        await m.reply_text(
            f"<b><u>💢 ᴇʀʀᴏʀ ᴏᴄᴄᴏᴜʀᴇᴅ!!</u>\n\nᴀᴜᴛᴏ ᴀᴅᴅᴇᴅ ʙᴏᴛ ᴏᴡɴᴇʀ ᴅᴇꜰᴜʟᴛ sʜᴏʀᴛɴᴇʀ\n\nɪꜰ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴄʜᴀɴɢᴇ ᴛʜᴇɴ ᴜsᴇ ᴄᴏʀʀᴇᴄᴛ ꜰᴏʀᴍᴀᴛ ᴏʀ ᴀᴅᴅ ᴠᴀʟɪᴅ sʜᴏʀᴛʟɪɴᴋ ᴅᴏᴍᴀɪɴ ɴᴀᴍᴇ & ᴀᴘɪ\n\nʏᴏᴜ ᴄᴀɴ ᴀʟsᴏ ᴄᴏɴᴛᴀᴄᴛ ᴏᴜʀ <a href=https://telegram.me/+JWsoDEJEB9EyNDU1>sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ</a> ꜰᴏʀ sᴏʟᴠᴇ ᴛʜɪs ɪssᴜᴇ...\n\nʟɪᴋᴇ -\n\n`/set_shortner_3 mdiskshortner.link e7beb3c8f756dfa15d0bec495abc65f58c0dfa95`\n\n💔 ᴇʀʀᴏʀ - <code>{e}</code></b>",
            quote=True,
        )


@Client.on_message(filters.command("set_log"))
async def set_log(client, message):
    grp_id = message.chat.id
    title = message.chat.title
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text("<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>")
    if len(message.text.split()) == 1:
        await message.reply(
            "<b><u>ɪɴᴠᴀɪʟᴅ ꜰᴏʀᴍᴀᴛ!!</u>\n\nᴜsᴇ ʟɪᴋᴇ ᴛʜɪs -\n`/log -100xxxxxxxx`</b>"
        )
        return
    sts = await message.reply("<b>♻️ ᴄʜᴇᴄᴋɪɴɢ...</b>")
    await asyncio.sleep(1.2)
    await sts.delete()
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")
    try:
        log = int(message.text.split(" ", 1)[1])
    except IndexError:
        return await message.reply_text(
            "<b><u>ɪɴᴠᴀɪʟᴅ ꜰᴏʀᴍᴀᴛ!!</u>\n\nᴜsᴇ ʟɪᴋᴇ ᴛʜɪs -\n`/log -100xxxxxxxx`</b>"
        )
    except ValueError:
        return await message.reply_text("<b>ᴍᴀᴋᴇ sᴜʀᴇ ɪᴅ ɪs ɪɴᴛᴇɢᴇʀ...</b>")
    try:
        t = await client.send_message(chat_id=log, text="<b>ʜᴇʏ ᴡʜᴀᴛ's ᴜᴘ!!</b>")
        await asyncio.sleep(3)
        await t.delete()
    except Exception as e:
        return await message.reply_text(
            f"<b><u>😐 ᴍᴀᴋᴇ sᴜʀᴇ ᴛʜɪs ʙᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜᴀᴛ ᴄʜᴀɴɴᴇʟ...</u>\n\n💔 ᴇʀʀᴏʀ - <code>{e}</code></b>"
        )
    await save_group_settings(grp_id, "log", log)
    await message.reply_text(
        f"<b>✅ sᴜᴄᴄᴇssꜰᴜʟʟʏ sᴇᴛ ʏᴏᴜʀ ʟᴏɢ ᴄʜᴀɴɴᴇʟ ꜰᴏʀ {title}\n\nɪᴅ `{log}`</b>",
        disable_web_page_preview=True,
    )
    user_id = m.from_user.id
    user_info = (
        f"@{m.from_user.username}" if m.from_user.username else f"{m.from_user.mention}"
    )
    link = (await client.get_chat(message.chat.id)).invite_link
    grp_link = f"[{message.chat.title}]({link})"
    log_message = f"#New_Log_Channel_Set\n\nName - {user_info}\nId - `{user_id}`\n\nLog channel id - `{log}`\nGroup link - {grp_link}"
    await client.send_message(
        LOG_API_CHANNEL, log_message, disable_web_page_preview=True
    )


@Client.on_message(filters.command("details"))
async def all_settings(client, message):
    grp_id = message.chat.id
    title = message.chat.title
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text("<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>")
    settings = await get_settings(grp_id)
    text = f"""<b><u>⚙️ ʏᴏᴜʀ sᴇᴛᴛɪɴɢs ꜰᴏʀ -</u> {title}

<u>✅️ 1sᴛ ᴠᴇʀɪꜰʏ sʜᴏʀᴛɴᴇʀ ɴᴀᴍᴇ/ᴀᴘɪ</u>
ɴᴀᴍᴇ - `{settings["shortner"]}`
ᴀᴘɪ - `{settings["api"]}`

<u>✅️ 2ɴᴅ ᴠᴇʀɪꜰʏ sʜᴏʀᴛɴᴇʀ ɴᴀᴍᴇ/ᴀᴘɪ</u>
ɴᴀᴍᴇ - `{settings["shortner_two"]}`
ᴀᴘɪ - `{settings["api_two"]}`

<u>✅️ 3ʀᴅ ᴠᴇʀɪꜰʏ sʜᴏʀᴛɴᴇʀ ɴᴀᴍᴇ/ᴀᴘɪ</u>
ɴᴀᴍᴇ - `{settings["shortner_three"]}`
ᴀᴘɪ - `{settings["api_three"]}`

🧭 𝟸ɴᴅ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴛɪᴍᴇ - `{settings['verify_time']}`

🧭 𝟹ʀᴅ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴛɪᴍᴇ - `{settings['third_verify_time']}`

📝 ʟᴏɢ ᴄʜᴀɴɴᴇʟ ɪᴅ - `{settings['log']}`

🌀 ꜰꜱᴜʙ ᴄʜᴀɴɴᴇʟ ɪᴅ - `{settings['fsub_id']}`

📍1 ᴛᴜᴛᴏʀɪᴀʟ ʟɪɴᴋ - {settings['tutorial']}

📍2 ᴛᴜᴛᴏʀɪᴀʟ ʟɪɴᴋ - {settings['tutorial_2']}

📍3 ᴛᴜᴛᴏʀɪᴀʟ ʟɪɴᴋ - {settings['tutorial_3']}

🎯 ɪᴍᴅʙ ᴛᴇᴍᴘʟᴀᴛᴇ - `{settings['template']}`

📂 ꜰɪʟᴇ ᴄᴀᴘᴛɪᴏɴ - `{settings['caption']}`</b>"""

    btn = [
        [InlineKeyboardButton("ʀᴇꜱᴇᴛ ᴅᴀᴛᴀ", callback_data="reset_grp_data")],
        [InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close_data")],
    ]
    reply_markup = InlineKeyboardMarkup(btn)
    dlt = await message.reply_text(
        text, reply_markup=reply_markup, disable_web_page_preview=True
    )
    await asyncio.sleep(300)
    await dlt.delete()


@Client.on_message(filters.command("set_time_2"))
async def set_time_2(client, message):
    userid = message.from_user.id if message.from_user else None
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")
    if not userid:
        return await message.reply("<b>ʏᴏᴜ ᴀʀᴇ ᴀɴᴏɴʏᴍᴏᴜꜱ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ...</b>")
    grp_id = message.chat.id
    title = message.chat.title
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text("<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>")
    try:
        time = int(message.text.split(" ", 1)[1])
    except:
        return await message.reply_text("Command Incomplete!")
    await save_group_settings(grp_id, "verify_time", time)
    await message.reply_text(
        f"Successfully set 1st verify time for {title}\n\nTime is - <code>{time}</code>"
    )


@Client.on_message(filters.command("set_time_3"))
async def set_time_3(client, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply("<b>ʏᴏᴜ ᴀʀᴇ ᴀɴᴏɴʏᴍᴏᴜꜱ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ...</b>")
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")
    grp_id = message.chat.id
    title = message.chat.title
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text("<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>")
    try:
        time = int(message.text.split(" ", 1)[1])
    except:
        return await message.reply_text("Command Incomplete!")
    await save_group_settings(grp_id, "third_verify_time", time)
    await message.reply_text(
        f"Successfully set 1st verify time for {title}\n\nTime is - <code>{time}</code>"
    )


@Client.on_callback_query(filters.regex("mostsearch"))
async def most(client, callback_query):
    def is_alphanumeric(string):
        return bool(re.match("^[a-zA-Z0-9 ]*$", string))

    limit = 20
    top_messages = await mdb.get_top_messages(limit)
    seen_messages = set()
    truncated_messages = []
    for msg in top_messages:
        msg_lower = msg.lower()
        if msg_lower not in seen_messages and is_alphanumeric(msg):
            seen_messages.add(msg_lower)

            if len(msg) > 35:
                truncated_messages.append(msg[:32] + "...")
            else:
                truncated_messages.append(msg)

    keyboard = [
        truncated_messages[i : i + 2] for i in range(0, len(truncated_messages), 2)
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        one_time_keyboard=True,
        resize_keyboard=True,
        placeholder="Most searches of the day",
    )

    await callback_query.message.reply_text(
        "<b>Hᴇʀᴇ ɪꜱ ᴛʜᴇ ᴍᴏꜱᴛ ꜱᴇᴀʀᴄʜᴇꜱ ʟɪꜱᴛ 👇</b>", reply_markup=reply_markup
    )
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^trending$"))
async def top(client, query):
    movie_series_names = await movie_series_db.get_movie_series_names(1)
    if not movie_series_names:
        await query.message.reply(
            "Tʜᴇʀᴇ ᴀʀᴇ ɴᴏ ᴍᴏᴠɪᴇ ᴏʀ sᴇʀɪᴇs ɴᴀᴍᴇs ᴀᴠᴀɪʟᴀʙʟᴇ ғᴏʀ ᴛʜᴇ ᴛᴏᴘ sᴇᴀʀᴄʜᴇs."
        )
        return
    buttons = [
        movie_series_names[i : i + 2] for i in range(0, len(movie_series_names), 2)
    ]
    spika = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    await query.message.reply(
        "<b>Here Is The Top Trending List 👇</b>", reply_markup=spika
    )


@Client.on_message(filters.command("refer"))
async def refer(bot, message):
    btn = [
        [
            InlineKeyboardButton(
                "• ɪɴᴠɪᴛᴇ ʟɪɴᴋ •",
                url=f"https://telegram.me/share/url?url=https://telegram.dog/{bot.me.username}?start=reff_{message.from_user.id}&text=Hello%21%20Experience%20a%20bot%20that%20offers%20a%20vast%20library%20of%20unlimited%20movies%20and%20series.%20%F0%9F%98%83",
            ),
            InlineKeyboardButton(
                f"⏳ {referdb.get_refer_points(message.from_user.id)}",
                callback_data="ref_point",
            ),
            InlineKeyboardButton("• ᴄʟᴏsᴇ •", callback_data="close_data"),
        ]
    ]
    m = await message.reply_sticker(
        "CAACAgQAAxkBAAEkt_Rl_7138tgHJdEsqSNzO5mPWioZDgACGRAAAudLcFGAbsHU3KNJUx4E"
    )
    await m.delete()
    reply_markup = InlineKeyboardMarkup(btn)
    await message.reply_photo(
        photo=random.choice(REFER_PICS),
        caption=f"👋Hay {message.from_user.mention},\n\nHᴇʀᴇ ɪꜱ ʏᴏᴜʀ ʀᴇғғᴇʀᴀʟ ʟɪɴᴋ:\nhttps://telegram.dog/{bot.me.username}?start=reff_{message.from_user.id}\n\nShare this link with your friends, Each time they join,  you will get 10 refferal points and after 100 points you will get 1 month premium subscription.",
        reply_markup=reply_markup,
        parse_mode=enums.ParseMode.HTML,
    )


@Client.on_message(filters.private & filters.command("pm_search_on"))
async def set_pm_search_on(client, message):
    user_id = message.from_user.id
    bot_id = client.me.id
    if user_id not in ADMINS:
        await message.delete()
        return

    await db.update_pm_search_status(bot_id, enable=True)
    await message.reply_text(
        "<b><i>✅️ ᴘᴍ ꜱᴇᴀʀᴄʜ ᴇɴᴀʙʟᴇᴅ, ꜰʀᴏᴍ ɴᴏᴡ ᴜꜱᴇʀꜱ ᴀʙʟᴇ ᴛᴏ ꜱᴇᴀʀᴄʜ ᴍᴏᴠɪᴇ ɪɴ ʙᴏᴛ ᴘᴍ.</i></b>"
    )


@Client.on_message(filters.private & filters.command("pm_search_off"))
async def set_pm_search_off(client, message):
    user_id = message.from_user.id
    bot_id = client.me.id
    if user_id not in ADMINS:
        await message.delete()
        return

    await db.update_pm_search_status(bot_id, enable=False)
    await message.reply_text(
        "<b><i>❌️ ᴘᴍ ꜱᴇᴀʀᴄʜ ᴅɪꜱᴀʙʟᴇᴅ, ꜰʀᴏᴍ ɴᴏᴡ ɴᴏ ᴏɴᴇ ᴄᴀɴ ᴀʙʟᴇ ᴛᴏ ꜱᴇᴀʀᴄʜ ᴍᴏᴠɪᴇ ɪɴ ʙᴏᴛ ᴘᴍ.</i></b>"
    )


@Client.on_message(filters.private & filters.command("movie_update_on"))
async def set_send_movie_on(client, message):
    user_id = message.from_user.id
    bot_id = client.me.id
    if user_id not in ADMINS:
        await message.delete()
        return
    await db.update_send_movie_update_status(bot_id, enable=True)
    await message.reply_text("<b><i>✅️ ꜱᴇɴᴅ ᴍᴏᴠɪᴇ ᴜᴘᴅᴀᴛᴇ ᴇɴᴀʙʟᴇᴅ.</i></b>")


@Client.on_message(filters.private & filters.command("movie_update_off"))
async def set_send_movie_update_off(client, message):
    user_id = message.from_user.id
    bot_id = client.me.id
    if user_id not in ADMINS:
        await message.delete()
        return
    await db.update_send_movie_update_status(bot_id, enable=False)
    await message.reply_text("<b><i>❌️ ꜱᴇɴᴅ ᴍᴏᴠɪᴇ ᴜᴘᴅᴀᴛᴇ ᴅɪꜱᴀʙʟᴇᴅ.</i></b>")


@Client.on_message(filters.command("verifyoff") & filters.user(ADMINS))
async def verifyoff(bot, message):
    chat_type = message.chat.type
    if chat_type == enums.ChatType.PRIVATE:
        return await message.reply_text("ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ᴡᴏʀᴋꜱ ᴏɴʟʏ ɪɴ ɢʀᴏᴜᴘꜱ !")
    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grpid = message.chat.id
        title = message.chat.title
    else:
        return
    await save_group_settings(grpid, "is_verify", False)
    return await message.reply_text("✓ ᴠᴇʀɪꜰʏ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴅɪꜱᴀʙʟᴇᴅ.")


@Client.on_message(filters.command("verifyon") & filters.user(ADMINS))
async def verifyon(bot, message):
    chat_type = message.chat.type
    if chat_type == enums.ChatType.PRIVATE:
        return await message.reply_text("ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ᴡᴏʀᴋꜱ ᴏɴʟʏ ɪɴ ɢʀᴏᴜᴘꜱ !")
    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grpid = message.chat.id
        title = message.chat.title
    else:
        return
    await save_group_settings(grpid, "is_verify", True)
    return await message.reply_text("✗ ᴠᴇʀɪꜰʏ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴇɴᴀʙʟᴇᴅ.")


@Client.on_message(filters.command("set_fsub"))
async def set_fsub(client, message):
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")
    grp_id = message.chat.id
    title = message.chat.title
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text("<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>")
    try:
        channel_id = int(message.text.split(" ", 1)[1])
    except IndexError:
        return await message.reply_text(
            "<b>ᴄᴏᴍᴍᴀɴᴅ ɪɴᴄᴏᴍᴘʟᴇᴛᴇ\n\nꜱᴇɴᴅ ᴍᴇ ᴄʜᴀɴɴᴇʟ ɪᴅ ᴡɪᴛʜ ᴄᴏᴍᴍᴀɴᴅ, ʟɪᴋᴇ <code>/set_fsub -100******</code></b>"
        )
    except ValueError:
        return await message.reply_text("<b>ᴍᴀᴋᴇ ꜱᴜʀᴇ ᴛʜᴇ ɪᴅ ɪꜱ ᴀɴ ɪɴᴛᴇɢᴇʀ.</b>")
    try:
        chat = await client.get_chat(channel_id)
    except Exception as e:
        return await message.reply_text(
            f"<b><code>{channel_id}</code> ɪꜱ ɪɴᴠᴀʟɪᴅ. ᴍᴀᴋᴇ ꜱᴜʀᴇ <a href=https://t.me/{temp.B_LINK} ʙᴏᴛ</a> ɪꜱ ᴀᴅᴍɪɴ ɪɴ ᴛʜᴀᴛ ᴄʜᴀɴɴᴇʟ\n\n<code>{e}</code></b>"
        )
    if chat.type != enums.ChatType.CHANNEL:
        return await message.reply_text(
            f"🫥 <code>{channel_id}</code> ᴛʜɪꜱ ɪꜱ ɴᴏᴛ ᴄʜᴀɴɴᴇʟ, ꜱᴇɴᴅ ᴍᴇ ᴏɴʟʏ ᴄʜᴀɴɴᴇʟ ɪᴅ ɴᴏᴛ ɢʀᴏᴜᴘ ɪᴅ</b>"
        )
    await save_group_settings(grp_id, "fsub_id", channel_id)
    mention = message.from_user.mention
    await client.send_message(
        LOG_API_CHANNEL,
        f"#Fsub_Channel_set\n\nᴜꜱᴇʀ - {mention} ꜱᴇᴛ ᴛʜᴇ ꜰᴏʀᴄᴇ ᴄʜᴀɴɴᴇʟ ꜰᴏʀ {title}:\n\nꜰꜱᴜʙ ᴄʜᴀɴɴᴇʟ - {chat.title}\nɪᴅ - `{channel_id}`",
    )
    await message.reply_text(
        f"<b>ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ꜱᴇᴛ ꜰᴏʀᴄᴇ ꜱᴜʙꜱᴄʀɪʙᴇ ᴄʜᴀɴɴᴇʟ ꜰᴏʀ {title}\n\nᴄʜᴀɴɴᴇʟ ɴᴀᴍᴇ - {chat.title}\nɪᴅ - <code>{channel_id}</code></b>"
    )


@Client.on_message(filters.command("remove_fsub"))
async def remove_fsub(client, message):
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")
    grp_id = message.chat.id
    title = message.chat.title
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text("<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>")
    settings = await get_settings(grp_id)
    if settings["fsub_id"] == AUTH_CHANNEL:
        await message.reply_text(
            "<b>ᴄᴜʀʀᴇɴᴛʟʏ ɴᴏ ᴀɴʏ ғᴏʀᴄᴇ ꜱᴜʙ ᴄʜᴀɴɴᴇʟ.... <code>[ᴅᴇғᴀᴜʟᴛ ᴀᴄᴛɪᴠᴀᴛᴇ]</code></b>"
        )
    else:
        await save_group_settings(grp_id, "fsub_id", AUTH_CHANNEL)
        mention = message.from_user.mention
        await client.send_message(
            LOG_API_CHANNEL,
            f"#Remove_Fsub_Channel\n\nᴜꜱᴇʀ - {mention} ʀᴇᴍᴏᴠᴇ ꜰꜱᴜʙ ᴄʜᴀɴɴᴇʟ ꜰʀᴏᴍ {title}",
        )
        await message.reply_text("<b>✅ ꜱᴜᴄᴄᴇꜱꜱғᴜʟʟʏ ʀᴇᴍᴏᴠᴇᴅ ꜰᴏʀᴄᴇ ꜱᴜʙ ᴄʜᴀɴɴᴇʟ.</b>")


@Client.on_message(filters.command("reset_group"))
async def reset_group_command(client, message):
    grp_id = message.chat.id
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text("<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>")
    sts = await message.reply("<b>♻️ ᴄʜᴇᴄᴋɪɴɢ...</b>")
    await asyncio.sleep(1.2)
    await sts.delete()
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")
    btn = [[InlineKeyboardButton("🚫 ᴄʟᴏsᴇ 🚫", callback_data="close_data")]]
    reply_markup = InlineKeyboardMarkup(btn)
    await save_default_settings(grp_id)
    await message.reply_text("ꜱᴜᴄᴄᴇꜱꜱғᴜʟʟʏ ʀᴇꜱᴇᴛ ɢʀᴏᴜᴘ ꜱᴇᴛᴛɪɴɢꜱ...")
