from vkbottle import Bot
from vkbottle.http import SingleAiohttpClient
from vkbottle.api import API
from aiohttp import TCPConnector
import asyncio
import dotenv
import os
from mistralai.client import Mistral
import requests



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
    
    response = requests.get("https://raw.githubusercontent.com/danakt/russian-words/master/russian.txt")
    russian_words = set(word.lower().strip() for word in response.text.split('\n') if word.strip())
    
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
        
        if word not in russian_words:
            await message.answer('Нет такого слова.')
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