import telebot
import requests
from telebot import types
from bs4 import BeautifulSoup as bs
from fake_useragent import UserAgent
from dotenv import load_dotenv
from keep_alive import keep_alive
import re
import os

load_dotenv()
keep_alive()

TOKEN = os.getenv('TOKEN')
bot = telebot.TeleBot(TOKEN)

user_links = {}
user_chapters = {}

headers = {
    'User-Agent': UserAgent().random,
    'Accept-Encoding': 'gzip, deflate',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
}

def search_manga(query):
    url = f'https://komikindo.lol/?s={query}'
    #headers = {'User-Agent': UserAgent().random}
    response = requests.get(url, headers=headers).text
    soup = bs(response, 'html.parser')
    find = soup.find_all('div', attrs={'class': 'animepost'})
    print(soup.prettify())
    manga_list = []
    for manga in find:
        thumbnail = manga.find('img')['src'] if manga.find('img') else 'No thumbnail'
        title = manga.find('h4').text if manga.find('h4') else 'No title'
        rating = manga.find('i').text if manga.find('i') else 'No rating'
        link = manga.find('a')['href'] if manga.find('a') else 'No link'
        
        data = {
            'thumbnail': thumbnail,
            'title': title,
            'rating': rating,
            'link': link
        }
        manga_list.append(data)

    return manga_list

def get_chapters(link):
    #headers = {'User-Agent': UserAgent().random}
    response = requests.get(link, headers=headers).text
    soup = bs(response, 'html.parser')
    chapter_list = soup.find('div', attrs={'class': 'bxcl scrolling', 'id': 'chapter_list'})

    chapters = []
    if chapter_list:
        chapter_items = chapter_list.find_all('li')
        for chapter in chapter_items:
            chapter_title = chapter.find('a').get_text(strip=True)
            chapter_link = chapter.find('a')['href']
            chapters.append((chapter_title, chapter_link))
    return chapters

def create_chapter_keyboard(chapters, page=0):
    markup = types.InlineKeyboardMarkup()
    start = page * 5
    end = start + 5
    for idx, (chapter_title, _) in enumerate(chapters[start:end], start=start):
        markup.add(types.InlineKeyboardButton(text=chapter_title, callback_data=f'chapter_{idx}'))
    
    navigation_buttons = []
    if page > 0:
        navigation_buttons.append(types.InlineKeyboardButton("⬅️ Prev", callback_data=f'prev_{page-1}'))
    if end < len(chapters):
        navigation_buttons.append(types.InlineKeyboardButton("➡️ Next", callback_data=f'next_{page+1}'))
    
    if navigation_buttons:
        markup.add(*navigation_buttons)
    
    return markup

def get_imgkomik(link):
    #headers = {'User-Agent': UserAgent().random}
    response = requests.get(link, headers=headers).text
    soup = bs(response, 'html.parser')
    find_div = soup.find('div', attrs={'class': 'img-landmine'})
    find_img = find_div.find_all('img') if find_div else []

    img_urls = []
    for img in find_img:
        source = img.get('src')
        img_urls.append(source)

    return img_urls

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    chat_member = bot.get_chat_member('@belajarpythonid', user_id)

    if chat_member.status in ['member', 'administrator', 'creator']:
        # Jika user sudah subscribe
        bot.send_chat_action(message.chat.id, 'typing')
        bot.send_message(message.chat.id, 'Hay, kamu! Gunakan perintah `/search <query>` untuk mencari manga.', parse_mode='Markdown')
    else:
        # Jika user belum subscribe
        markup = types.InlineKeyboardMarkup()
        subscribe_button = types.InlineKeyboardButton('Subscribe Channel', url='https://t.me/belajarpythonid')
        markup.add(subscribe_button)
        bot.send_chat_action(message.chat.id, 'typing')
        bot.send_message(message.chat.id, 'Hey kamu belum subscribe. Subscribe dulu yaa sebelum melanjutkan!', reply_markup=markup)
        
@bot.message_handler(commands=['search'])
def handle_search(message):
    query = message.text.split(' ', 1)
    if len(query) < 2:
        bot.send_chat_action(message.chat.id, 'typing')
        bot.reply_to(message, 'Gunakan format `/search <query>` untuk mencari manga.', parse_mode='Markdown')
        return

    manga_query = query[1]
    manga_list = search_manga(manga_query)

    if not manga_list:
        bot.send_chat_action(message.chat.id, 'typing')
        bot.reply_to(message, 'Tidak ada manga yang ditemukan.')
        return

    for manga in manga_list:
        thumbnail_url = manga['thumbnail']
        image_response = requests.get(thumbnail_url, stream=True)
        
        if image_response.status_code == 200:
            with open('thumbnail.jpg', 'wb') as file:
                for chunk in image_response.iter_content(1024):
                    file.write(chunk)

            caption = f"Title: *{manga['title']}*\nRating: *{manga['rating']}*\nLink: `{manga['link']}`"
            
            with open('thumbnail.jpg', 'rb') as photo:
                bot.send_chat_action(message.chat.id, 'upload_photo')
                bot.send_photo(message.chat.id, photo, caption=caption, parse_mode='Markdown')
            
            os.remove('thumbnail.jpg')
        else:
            bot.send_chat_action(message.chat.id, 'typing')
            bot.reply_to(message, 'Thumbnail tidak dapat diunduh.')
            
    markup = types.ForceReply(selective=False)
    bot.send_chat_action(message.chat.id, 'typing')
    bot.send_message(message.chat.id, 'Copy dan paste link manga dan kirim ke aku ya', reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    url_pattern = re.compile(r'(https?://\S+)')
    match = url_pattern.search(message.text)

    if match:
        link = match.group(0)
        user_links[message.chat.id] = link  # Simpan link manga berdasarkan chat ID
        chapters = get_chapters(link)
        if chapters:
            user_chapters[message.chat.id] = chapters  # Simpan chapters berdasarkan chat ID
            markup = create_chapter_keyboard(chapters, page=0)
            bot.send_chat_action(message.chat.id, 'typing')
            bot.send_message(message.chat.id, 'Chapter tersedia:', reply_markup=markup)
        else:
            bot.send_chat_action(message.chat.id, 'typing')
            bot.reply_to(message, 'Tidak ada chapter yang ditemukan untuk link ini.')
    else:
        bot.send_chat_action(message.chat.id, 'typing')
        bot.reply_to(message, "Perintah tidak valid. Gunakan format /search <query> untuk mencari manga.")

@bot.callback_query_handler(func=lambda call: call.data.startswith(('chapter_', 'next_', 'prev_')))
def handle_pagination_or_chapter(call):
    bot.answer_callback_query(call.id)
    
    if call.data.startswith('chapter_'):
        chapter_idx = int(call.data.split('_')[1])
        chapters = user_chapters.get(call.message.chat.id, [])
        chapter_title, chapter_link = chapters[chapter_idx]
        img_urls = get_imgkomik(chapter_link)

        if img_urls:
            for img_url in img_urls:
                img_data = requests.get(img_url).content
                with open('comic_image.jpg', 'wb') as file:
                    file.write(img_data)
                with open('comic_image.jpg', 'rb') as img_file:
                    bot.send_chat_action(call.message.chat.id, 'upload_photo')
                    bot.send_photo(call.message.chat.id, img_file)
                os.remove('comic_image.jpg')
            
            bot.send_chat_action(call.message.chat.id, 'typing')
            bot.send_message(call.message.chat.id, f"Ini adalah komik untuk {chapter_title}. Happy reading and enjoy!")
        else:
            bot.send_chat_action(call.message.chat.id, 'typing')
            bot.send_message(call.message.chat.id, "Tidak ada gambar yang ditemukan untuk chapter ini.")
    else:
        action, page = call.data.split('_')
        page = int(page)

        chapters = user_chapters.get(call.message.chat.id)
        if chapters:
            markup = create_chapter_keyboard(chapters, page=page)
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

bot.infinity_polling()
