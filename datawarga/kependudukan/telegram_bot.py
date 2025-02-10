from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, 
    MessageHandler, filters, ConversationHandler
)
from django.conf import settings
import logging
import requests
import json
from datetime import datetime
from kependudukan.models import TransaksiIuranBulanan
import tempfile
import os

logger = logging.getLogger(__name__)

# Define states for conversation
ALAMAT, BULAN, TAHUN, JUMLAH, BUKTI, KONFIRMASI = range(6)

# Store temporary data
payment_data = {}

def is_user_allowed(username: str) -> bool:
    """Check if username is in the allowed users list"""
    if not settings.TELEGRAM_ALLOWED_USERS or settings.TELEGRAM_ALLOWED_USERS == ['']:
        logger.warning("No allowed users configured")
        return False
    return username in settings.TELEGRAM_ALLOWED_USERS

async def check_access(update: Update) -> bool:
    """Check if user has access and send rejection message if not"""
    username = update.effective_user.username
    if not is_user_allowed(username):
        await update.message.reply_text(
            'Maaf, Anda tidak memiliki akses ke bot ini. '
            'Silakan hubungi admin untuk mendapatkan akses.'
        )
        logger.warning(f"Unauthorized access attempt from @{username}")
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update):
        return

    await update.message.reply_text(
        'Selamat datang di Data Warga Bot!\n\n'
        'Gunakan perintah berikut:\n'
        '/cari <nama/nik/blok> - Mencari data warga\n'
        '/rumah <blok/nomor> - Mencari data penghuni rumah\n'
        '/iuran <blok/nomor> [tahun] - Cek status iuran rumah\n'
        'Contoh:\n'
        '/cari John\n'
        '/cari 3674xxx\n'
        '/rumah J2/5\n'
        '/iuran J2/5 2024\n'
        '/bayar\n'
    )

async def search_warga(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update):
        return

    if not context.args:
        await update.message.reply_text('Masukkan kata kunci pencarian. Contoh: /cari John')
        return

    search_term = ' '.join(context.args)
    
    try:
        # Get JWT token
        token_response = requests.post(
            f'{settings.SITE_URL}/api/token/',
            data={
                'username': settings.BOT_API_USER,
                'password': settings.BOT_API_PASS
            }
        )
        
        # Add token response logging
        logger.info(f"Token response status: {token_response.status_code}")
        if token_response.status_code != 200:
            logger.error(f"Token response error: {token_response.text}")
            await update.message.reply_text('Gagal autentikasi dengan sistem.')
            return
            
        try:
            token = token_response.json()['access']
        except (KeyError, json.JSONDecodeError) as e:
            logger.error(f"Failed to parse token response: {str(e)}")
            logger.error(f"Token response content: {token_response.text}")
            await update.message.reply_text('Gagal mendapatkan token akses.')
            return

        # Search warga using internal API
        headers = {'Authorization': f'Bearer {token}'}
        search_response = requests.post(
            f'{settings.SITE_URL}/api/warga/search/',
            headers=headers,
            json={'search': search_term}
        )
        
        # Add search response logging
        logger.info(f"Search response status: {search_response.status_code}")
        if search_response.status_code != 200:
            logger.error(f"Search response error: {search_response.text}")
            await update.message.reply_text('Terjadi kesalahan saat mencari data.')
            return
            
        try:
            warga_list = search_response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse search response: {str(e)}")
            logger.error(f"Search response content: {search_response.text}")
            await update.message.reply_text('Gagal memproses hasil pencarian.')
            return

        if not warga_list:
            await update.message.reply_text('Tidak ditemukan data warga.')
            return

        # Format response
        response = 'Hasil pencarian:\n\n'
        for warga in warga_list[:5]:  # Limit to 5 results
            response += f"Nama: {warga['nama_lengkap']}\n"
            response += f"NIK: {warga['nik']}\n"
            if warga['kompleks']:
                response += f"Alamat: Blok {warga['kompleks']['blok']}/{warga['kompleks']['nomor']}\n"
            response += f"Status: {warga['status_tinggal']}\n"
            response += "-------------------\n"

        if len(warga_list) > 5:
            response += f"\nDan {len(warga_list) - 5} data lainnya..."

        await update.message.reply_text(response)
            
    except Exception as e:
        logger.error(f"Telegram bot error: {str(e)}", exc_info=True)
        await update.message.reply_text('Terjadi kesalahan sistem.')

async def search_rumah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update):
        return

    if not context.args:
        await update.message.reply_text('Masukkan alamat rumah. Contoh: /rumah J2/5')
        return

    search_term = ' '.join(context.args)
    if '/' not in search_term:
        await update.message.reply_text('Format alamat salah. Gunakan format: Blok/Nomor (contoh: J2/5)')
        return
    
    try:
        # Get JWT token
        token_response = requests.post(
            f'{settings.SITE_URL}/api/token/',
            data={
                'username': settings.BOT_API_USER,
                'password': settings.BOT_API_PASS
            }
        )
        
        logger.info(f"Token response status: {token_response.status_code}")
        if token_response.status_code != 200:
            logger.error(f"Token response error: {token_response.text}")
            await update.message.reply_text('Gagal autentikasi dengan sistem.')
            return
            
        try:
            token = token_response.json()['access']
        except (KeyError, json.JSONDecodeError) as e:
            logger.error(f"Failed to parse token response: {str(e)}")
            logger.error(f"Token response content: {token_response.text}")
            await update.message.reply_text('Gagal mendapatkan token akses.')
            return

        # Search kompleks using internal API
        headers = {'Authorization': f'Bearer {token}'}
        search_response = requests.post(
            f'{settings.SITE_URL}/api/kompleks/warga/',
            headers=headers,
            json={'blok_no': search_term}
        )
        
        logger.info(f"Search response status: {search_response.status_code}")
        if search_response.status_code != 200:
            if search_response.status_code == 204:
                await update.message.reply_text(
                    f'Alamat Blok {search_term} tidak terdaftar.\n'
                    'Pastikan format penulisan benar (contoh: J2/5)'
                )
            else:
                logger.error(f"Search response error: {search_response.text}")
                await update.message.reply_text('Terjadi kesalahan saat mencari data.')
            return
            
        try:
            warga_list = search_response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse search response: {str(e)}")
            logger.error(f"Search response content: {search_response.text}")
            await update.message.reply_text('Gagal memproses hasil pencarian.')
            return

        if not warga_list:
            await update.message.reply_text('Tidak ada penghuni di alamat tersebut.')
            return

        # Format response
        response = f'Daftar Penghuni {search_term}:\n\n'
        for warga in warga_list:
            response += f"Nama: {warga['nama_lengkap']}\n"
            if warga.get('status_keluarga'):
                response += f"Status: {warga['status_keluarga']}\n"
            if warga.get('kepala_keluarga'):
                response += "👥 Kepala Keluarga\n"
            response += "-------------------\n"

        await update.message.reply_text(response)
            
    except Exception as e:
        logger.error(f"Telegram bot error: {str(e)}", exc_info=True)
        await update.message.reply_text('Terjadi kesalahan sistem.')

async def check_iuran(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update):
        return

    if not context.args:
        await update.message.reply_text('Masukkan alamat rumah. Contoh: /iuran J2/5 2024')
        return

    # Get current year if not specified
    current_year = datetime.now().strftime("%Y")
    
    if len(context.args) >= 2:
        search_term = context.args[0]
        year = context.args[1]
    else:
        search_term = context.args[0]
        year = current_year
    
    if '/' not in search_term:
        await update.message.reply_text('Format alamat salah. Gunakan format: Blok/Nomor (contoh: J2/5)')
        return
    
    try:
        # Get JWT token
        token_response = requests.post(
            f'{settings.SITE_URL}/api/token/',
            data={
                'username': settings.BOT_API_USER,
                'password': settings.BOT_API_PASS
            }
        )
        
        logger.info(f"Token response status: {token_response.status_code}")
        if token_response.status_code != 200:
            logger.error(f"Token response error: {token_response.text}")
            await update.message.reply_text('Gagal autentikasi dengan sistem.')
            return
            
        try:
            token = token_response.json()['access']
        except (KeyError, json.JSONDecodeError) as e:
            logger.error(f"Failed to parse token response: {str(e)}")
            logger.error(f"Token response content: {token_response.text}")
            await update.message.reply_text('Gagal mendapatkan token akses.')
            return

        # Get iuran history using internal API
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        search_response = requests.post(
            f'{settings.SITE_URL}/api/kompleks/iuran/',
            headers=headers,
            json={
                'blok_no': search_term,
                'tahun': year
            }
        )
        
        logger.info(f"Search response status: {search_response.status_code}")
        if search_response.status_code != 200:
            if search_response.status_code == 204:
                await update.message.reply_text(
                    f'Alamat Blok {search_term} tidak terdaftar.\n'
                    'Pastikan format penulisan benar (contoh: J2/5)'
                )
            else:
                logger.error(f"Search response error: {search_response.text}")
                await update.message.reply_text('Terjadi kesalahan saat mencari data.')
            return
            
        try:
            iuran_list = search_response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse search response: {str(e)}")
            logger.error(f"Search response content: {search_response.text}")
            await update.message.reply_text('Gagal memproses hasil pencarian.')
            return

        if not iuran_list:
            await update.message.reply_text(f'Belum ada pembayaran iuran untuk {search_term} di tahun {year}.')
            return

        # Format response
        response = f'Status Iuran {search_term} Tahun {year}:\n\n'
        
        # Create month mapping
        months_paid = {iuran['periode_bulan']: iuran for iuran in iuran_list}
        
        # List all months with status
        for month_num, month_name in TransaksiIuranBulanan.LIST_BULAN:
            status = '✅' if month_num in months_paid else '❌'
            response += f"{status} {month_name}\n"
            if month_num in months_paid:
                iuran = months_paid[month_num]
                response += f"   💰 Rp {iuran['total_bayar']:,}\n"
                if iuran.get('keterangan'):
                    response += f"   📝 {iuran['keterangan']}\n"
        
        # Add summary
        total_paid = len(months_paid)
        response += f"\nTotal: {total_paid}/12 bulan"

        await update.message.reply_text(response)
            
    except Exception as e:
        logger.error(f"Telegram bot error: {str(e)}", exc_info=True)
        await update.message.reply_text('Terjadi kesalahan sistem.')

async def bayar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update):
        return ConversationHandler.END
    
    await update.message.reply_text(
        'Mari catat pembayaran iuran.\n'
        'Masukkan alamat rumah (contoh: J2/5):'
    )
    return ALAMAT

async def alamat_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    search_term = update.message.text
    if '/' not in search_term:
        await update.message.reply_text('Format alamat salah. Gunakan format: Blok/Nomor (contoh: J2/5)')
        return ALAMAT
    
    payment_data[update.effective_user.id] = {'alamat': search_term}
    
    # Show month options
    months = [f"{num} - {name}" for num, name in TransaksiIuranBulanan.LIST_BULAN]
    keyboard = [[month] for month in months]
    await update.message.reply_text(
        'Pilih bulan pembayaran:',
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    )
    return BULAN

async def bulan_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bulan = update.message.text.split(' - ')[0]  # Get month number
    payment_data[update.effective_user.id]['bulan'] = bulan
    
    await update.message.reply_text(
        'Masukkan tahun pembayaran:',
        reply_markup=ReplyKeyboardRemove()
    )
    return TAHUN

async def tahun_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tahun = int(update.message.text)
        if tahun < 2000 or tahun > 2100:
            raise ValueError
    except ValueError:
        await update.message.reply_text('Tahun tidak valid. Masukkan tahun dengan format YYYY (contoh: 2024)')
        return TAHUN
    
    payment_data[update.effective_user.id]['tahun'] = tahun
    await update.message.reply_text(
        f'Masukkan jumlah pembayaran (default: {settings.IURAN_BULANAN}):'
    )
    return JUMLAH

async def jumlah_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        jumlah = int(update.message.text)
    except ValueError:
        await update.message.reply_text('Jumlah tidak valid. Masukkan angka saja.')
        return JUMLAH
    
    payment_data[update.effective_user.id]['jumlah'] = jumlah
    await update.message.reply_text(
        'Upload foto bukti pembayaran:'
    )
    return BUKTI

async def bukti_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not update.message.photo:
        await update.message.reply_text('Mohon kirim foto bukti pembayaran.')
        return BUKTI
    
    # Get the largest photo (best quality)
    photo = update.message.photo[-1]
    
    # Download photo
    file = await context.bot.get_file(photo.file_id)
    
    # Create temp file with unique name
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"receipt_{user_id}_{photo.file_unique_id}.jpg")
    await file.download_to_drive(temp_path)
    
    payment_data[user_id]['bukti_path'] = temp_path
    
    # Show confirmation
    data = payment_data[user_id]
    await update.message.reply_text(
        f'Konfirmasi pembayaran:\n\n'
        f'Alamat: {data["alamat"]}\n'
        f'Periode: {data["bulan"]}/{data["tahun"]}\n'
        f'Jumlah: Rp {data["jumlah"]:,}\n\n'
        f'Ketik "ya" untuk konfirmasi atau "tidak" untuk membatalkan:'
    )
    return KONFIRMASI

async def konfirmasi_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if update.message.text.lower() != 'ya':
        if user_id in payment_data:
            # Clean up temp file
            if 'bukti_path' in payment_data[user_id]:
                try:
                    os.remove(payment_data[user_id]['bukti_path'])
                except:
                    pass
            del payment_data[user_id]
        await update.message.reply_text('Pembayaran dibatalkan.')
        return ConversationHandler.END
    
    data = payment_data[user_id]
    
    try:
        # Get JWT token
        token_response = requests.post(
            f'{settings.SITE_URL}/api/token/',
            data={
                'username': settings.BOT_API_USER,
                'password': settings.BOT_API_PASS
            }
        )
        
        if token_response.status_code != 200:
            raise Exception("Authentication failed")
            
        token = token_response.json()['access']
        
        # Create multipart form data
        files = {
            'bukti_bayar': ('receipt.jpg', open(data['bukti_path'], 'rb'), 'image/jpeg')
        }
        payload = {
            'blok_no': data['alamat'],
            'periode_bulan': data['bulan'],
            'periode_tahun': data['tahun'],
            'total_bayar': data['jumlah']
        }
        
        # Record payment using internal API
        headers = {
            'Authorization': f'Bearer {token}',
        }
        payment_response = requests.post(
            f'{settings.SITE_URL}/api/kompleks/bayar/',
            headers=headers,
            data=payload,
            files=files
        )
        
        if payment_response.status_code == 404:
            await update.message.reply_text(
                f'Alamat Blok {data["alamat"]} tidak terdaftar.\n'
                'Pastikan format penulisan benar (contoh: J2/5)'
            )
        elif payment_response.status_code == 400:
            error_msg = payment_response.json().get('error', 'Pembayaran tidak valid')
            await update.message.reply_text(f'Error: {error_msg}')
        elif payment_response.status_code != 200:
            await update.message.reply_text('Terjadi kesalahan saat mencatat pembayaran.')
        else:
            await update.message.reply_text('✅ Pembayaran berhasil dicatat!')
            
    except Exception as e:
        logger.error(f"Payment error: {str(e)}", exc_info=True)
        await update.message.reply_text('Terjadi kesalahan sistem.')
    finally:
        # Clean up
        if 'bukti_path' in data:
            try:
                os.remove(data['bukti_path'])
            except:
                pass
        del payment_data[user_id]
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in payment_data:
        # Clean up temp file
        if 'bukti_path' in payment_data[user_id]:
            try:
                os.remove(payment_data[user_id]['bukti_path'])
            except:
                pass
        del payment_data[user_id]
    
    await update.message.reply_text(
        'Pembayaran dibatalkan.',
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def run_telegram_bot():
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not configured")
        return
        
    if not settings.BOT_API_USER or not settings.BOT_API_PASS:
        logger.error("Bot API credentials not configured")
        return
        
    if not settings.SITE_URL:
        logger.error("SITE_URL not configured")
        return

    if not settings.TELEGRAM_ALLOWED_USERS or settings.TELEGRAM_ALLOWED_USERS == ['']:
        logger.warning("No allowed users configured, bot will reject all requests")

    try:
        app = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()
        
        # Create conversation handler
        payment_conv = ConversationHandler(
            entry_points=[CommandHandler('bayar', bayar)],
            states={
                ALAMAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, alamat_input)],
                BULAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, bulan_input)],
                TAHUN: [MessageHandler(filters.TEXT & ~filters.COMMAND, tahun_input)],
                JUMLAH: [MessageHandler(filters.TEXT & ~filters.COMMAND, jumlah_input)],
                BUKTI: [MessageHandler(filters.PHOTO, bukti_input)],
                KONFIRMASI: [MessageHandler(filters.TEXT & ~filters.COMMAND, konfirmasi_input)],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )
        
        # Add handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("cari", search_warga))
        app.add_handler(CommandHandler("rumah", search_rumah))
        app.add_handler(CommandHandler("iuran", check_iuran))
        app.add_handler(payment_conv)  # Add conversation handler
        
        logger.info("Telegram bot started successfully")
        # Start the bot
        app.run_polling()
    except Exception as e:
        logger.error(f"Failed to start Telegram bot: {str(e)}") 