from vkbottle import Bot
from vkbottle.http import SingleAiohttpClient
from vkbottle.api import API
from aiohttp import TCPConnector
import asyncio
import dotenv
import os
from mistralai import Mistral
import re  # Модуль для проверки, что слово состоит только из русских букв

def main():
    dotenv.load_dotenv()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    VK_key = os.getenv('VK_API_KEY')
    Mistral_key = os.getenv("MISTRAL_API_KEY")
    
    client = Bot(
        api=API(
            token=VK_key,
            http_client=SingleAiohttpClient(
                connector=TCPConnector(ssl=False, loop=loop)
            )
        )
    )
    
    # Словарь больше не загружаем!
    is_game_started = False
    used_words = set()
    last_bot_word = None
    mistral = Mistral(api_key=Mistral_key)
    messages = [{"role": "system", "content": "Ты игрок в слова. Отвечай одним словом на русском языке на последнюю букву слова пользователя (если ъ,ь,ы - то предпоследнюю). Не повторяй свои предыдущие слова."}]
    
    def get_last_letter(word):
        for i in reversed(word.lower()):
            if i not in ['ь', 'ъ', 'ы']:
                return i
        return None
    
    def is_likely_russian_noun(word):
        """Проверяет, похоже ли слово на русское существительное"""
        # Слишком короткие или длинные
        if len(word) < 2 or len(word) > 15:
            return False
        
        # Только русские буквы
        if not re.match(r'^[а-яё]+$', word.lower()):
            return False
        
        # Окончания прилагательных и причастий (НЕ существительные)
        bad_endings = ('ый', 'ий', 'ой', 'ая', 'яя', 'ое', 'ее', 'ые', 'ие',
                       'ого', 'ему', 'им', 'ом', 'ую', 'ых', 'ыми',
                       'вший', 'вшая', 'вшее', 'вшие', 'вшим')
        
        if word.endswith(bad_endings):
            return False
        
        # Все остальные слова считаем существительными
        return True
    
    @client.on.private_message(text="/start")
    async def start_game(message):
        nonlocal is_game_started, used_words, last_bot_word, messages
        messages = [messages[0]]
        used_words.clear()
        last_bot_word = None
        is_game_started = True     
        await message.answer('Игра пошла, скажи любое слово. /stop - остановить')
    
    @client.on.private_message(text="/stop")
    async def stop_game(message):
        nonlocal is_game_started
        is_game_started = False
        await message.answer('Игра остановлена.')
        
    @client.on.private_message()
    async def chat_with_user(message):
        nonlocal is_game_started, used_words, last_bot_word, messages
        
        if not is_game_started:
            await message.answer('Напиши "/start"')
            return
        
        word = message.text.strip().lower()
        
        if ' ' in word or len(word) < 2:
            await message.answer('Одно слово, длиннее 1 буквы.')
            return
        
        # Проверяем, похоже ли слово на существительное
        if not is_likely_russian_noun(word):
            await message.answer('Нужно русское существительное.')
            return
        
        if word in used_words:
            await message.answer('Уже было.')
            return
        
        if last_bot_word and word[0] != get_last_letter(last_bot_word):
            await message.answer(f'Начинай на "{get_last_letter(last_bot_word)}"')
            return
        
        used_words.add(word)
        messages.append({"role": "user", "content": word})
        
        res = mistral.chat.complete(model="mistral-small-latest", messages=messages, stream=False)
        bot_word = res.choices[0].message.content.lower()
        
        if bot_word in used_words:
            messages.append({"role": "user", "content": f"Слово '{bot_word}' уже было. Напиши другое слово."})
            res = mistral.chat.complete(model="mistral-small-latest", messages=messages, stream=False)
            bot_word = res.choices[0].message.content.lower()
        
        used_words.add(bot_word)
        last_bot_word = bot_word
        messages.append({"role": "assistant", "content": bot_word})
        await message.answer(bot_word)
        
    client.run_forever()

if __name__ == '__main__':
    main()
