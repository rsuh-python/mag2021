import re
import urllib.request
import pickle
import os
from time import sleep
from bs4 import BeautifulSoup as bs
from dataclasses import dataclass


'''dataclass - это декоратор класса, который позволяет в упрощенном виде создавать класс для хранения данных. Будем хранить в нем свои тексты'''

@dataclass 
class Text:
    author: str
    title: str
    year: str
    text: str


# создаем кастомное исключение
class UnknownFileExtension(Exception): pass


class Scraper:
    """
    Основной класс скрейпера
    mainpage: страница, с которой начинаем скрейпить. Предполагается, что заканчивается на /
    encoding: кодировка страницы
    textre: регулярное выражение для тех адресов страниц, которые содержат нужные нам тексты
    attributes: функция, которая обязана возвращать четыре наших атрибута текста именно в том порядке, в каком они перечислены в классе Text
    """
    def __init__(self, mainpage: str, encoding: str, textre, attributes):
        self.mainpage = mainpage 
        self.encoding = encoding 
        self.textre = textre
        self.attributes = attributes
        self.viewed = set() # задаем пустое множество просмотренных ссылок
        self.texts = [] # и пустой список собранных текстов
        self.counter = 0 # это чисто служебная переменная для очистки консоли

    def _crawl(self, page, n=10):
        """Рекурсивная функция краулинга: внутренняя реализация"""
        '''В этом месте происходит очистка консоли, как только вывод достигает 10 строчек (можно это поменять)'''
        self.counter += 1
        if self.counter > 10:
            os.system('cls')
            self.counter = 0

        print(page) # логируем страницу, которую краулим

        # открываем страницу, читаем ее, добавляем в просмотренные
        fid = urllib.request.urlopen(page) 
        webpage = fid.read().decode(self.encoding)
        self.viewed.add(page)
        soup = bs(webpage, 'html.parser') 

        # проверяем, нужно ли нам с нее скачать текст
        if re.match(self.textre, page):
            self.texts.append(Text(*self.attributes(soup, page))) # распаковка нужна, потому что наша функция возвращает кортеж из нужных нам атрибутов
            print(f'text for {page} added!')

        # собираем линки с текущей страницы
        links = []
        for link in soup.find_all('a', attrs={'href': re.compile(r'^/.+')}):
            l = self.mainpage[:-1] + link.get('href')
            if l not in self.viewed:
                links.append(l)

        # если линки не пустые, то идем рекурсивно по линкам
        if links:
            for link in links:
                if re.search('board|login|help|topic|type|about', link): # мы, вероятно, не хотим бесконечно лазать по внутренностям не интересующих нас разделов
                    continue
                if len(self.texts) > n:  # n - число текстов, которое мы хотим выкачать
                    return
                sleep(0.5)  # чтоб нас случайно не заблочили как робота
                self._crawl(link, n)  # рекурсивный вызов функции
        else:
            return 

    def crawl(self, n=10):
        """Внешняя функция-интерфейс"""
        print('Crawling started')
        self._crawl(self.mainpage, n)  # уходим во внутреннюю рекурсивную функцию

    def writetexts(self, path):
        """Простенькая запись результата: зависит от того, какое расширение в пути мы укажем"""
        if path.endswith('bin'):
            pickle.dump(self.texts, open(path, 'wb'))
        elif path.endswith('txt'):
            with open(path, 'w', encoding='utf8') as file:
                for text in self.texts:
                    print(text, file=file)
        else:
            raise UnknownFileExtension('Я не умею записывать такие файлы')


def attributes(soup, page):
    """Эту функцию мы должны передавать в наш краулер для того, чтобы извлекать с ее помощью нужные нам атрибуты"""
    ta = re.search(r'(.+?) \((.+?)\) / Проза.ру', soup.title.string) # расчленяем заголовок на автора и название с помощью групп в регулярках
    if ta:
        title = ta.group(1)
        author = ta.group(2)
    else:
        # а вдруг мы где-то накосячили с регуляркой
        title = 'Unknown'
        author = 'Unknown'
    year = re.search(r'https://proza.ru/(\d{4}/\d\d/\d\d)/.*', page).group(1) # получаем год с помощью группы
    text = '\n'.join((elem.text for elem in soup.find_all("div", {"class": "text"})))  # собираем все возможные сегменты класса "текст" с помощью bs4
    return author, title, year, text


def main():
    """Стартовая точка: создаем краулер, скрейпим и тут же сохраняем тексты"""
    crawler = Scraper('https://proza.ru/', 'cp1251', re.compile(r'https://proza.ru/\d{4}/\d\d/\d\d/.*'), attributes)
    crawler.crawl()
    crawler.writetexts(input('Введите имя файла для записи: '))

if __name__ == '__main__':
    main()