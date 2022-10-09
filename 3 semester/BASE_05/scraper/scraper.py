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
    ndump: количество текстов, при котором нужно делать дамп и очищать оперативную память
    viewed: если у нас это не первый фетч, нужно добавить просмотренные ссылки
    """
    def __init__(self, mainpage: str, *, encoding: str, textre, attributes, ndump=100, viewed=set()):
        self.mainpage = mainpage 
        self.encoding = encoding 
        self.textre = textre
        self.attributes = attributes
        self.ndump = ndump
        self.viewed = viewed # задаем множество просмотренных ссылок
        self.texts = [] # и пустой список собранных текстов
        self.counter = 0 # это чисто служебная переменная для очистки консоли
        self.recursioncount = 0  # обычно ограничение глубины рекурсии - 1000. Нам придется за этим следить
        self.writecount = 0 # это переменная для записи дампов
        self.totalcount = 0
        self.ext = 'bin'  # расширение файлов для дампов по умолчанию

    def _crawl(self, page, n=10):
        """Рекурсивная функция краулинга: внутренняя реализация"""
        '''В этом месте происходит очистка консоли, как только вывод достигает 10 строчек (можно это поменять)'''
        self.counter += 1 # нужно закомментировать, если не хотим логировать все страницы подряд
        if self.counter > 10:
            os.system('cls')  # команда для linux & macos может отличаться. Для linux - clear
            self.counter = 0

        # если количество скрауленных текстов больше ndump, делаем дамп, чтобы не хранить их в оперативе
        if len(self.texts) >= self.ndump:
            self.writetexts(f'part_{self.writecount}.{self.ext}')
            self.texts = []

        print(page) # логируем страницу, которую краулим

        # открываем страницу, читаем ее, добавляем в просмотренные
        try:
            fid = urllib.request.urlopen(page) 
            webpage = fid.read().decode(self.encoding)
        except urllib.error.URLError:  # может возникнуть ошибка, когда сайт долго не отвечает на запрос: отлавливаем ее и ждем 5 секунд
            print(f'Connection trouble, page {page}. Waiting...')
            sleep(5)
            return
        except UnicodeEncodeError: # если вдруг возникла проблема с кодировкой
            print(f'Encoding Error, page {page}, leaving out')
            self.viewed.add(page)
            return
        self.viewed.add(page)
        soup = bs(webpage, 'html.parser') 

        # проверяем, нужно ли нам с нее скачать текст
        if re.match(self.textre, page):
            self.texts.append(Text(*self.attributes(soup, page))) # распаковка нужна, потому что наша функция возвращает кортеж из нужных нам атрибутов
            self.totalcount += 1
            self.writecount += 1
            # self.counter += 1  # если включаем логирование всех просматриваемых страниц, это нужно закомментировать, а верхний - наоборот
            print(f'Text for {page} added! Total amount scraped: {self.totalcount}.')

        # собираем линки с текущей страницы
        links = set()
        for link in soup.find_all('a', attrs={'href': re.compile(r'^/.+')}):
            l = self.mainpage[:-1] + link.get('href')
            if l not in self.viewed:
                links.add(l)

        # если линки не пустые, то идем рекурсивно по линкам
        if links:
            for link in links:
                if re.search('board|login|help|topic|type|about', link): # мы, вероятно, не хотим бесконечно лазать по внутренностям не интересующих нас разделов
                    continue
                if self.totalcount >= n:  # n - число текстов, которое мы хотим выкачать
                    return
                if self.recursioncount == 500:  # устанавливаем максимальную глубину рекурсии 500. Дойдя до этой глубины, на ней и останемся. 
                    self.recursioncount -= 1  # это нужно, чтобы совсем не вылететь из функции
                    return
                sleep(0.5)  # чтоб нас случайно не заблочили как робота
                self.recursioncount += 1 # углубляемси
                self._crawl(link, n)  # рекурсивный вызов функции
        else:
            self.recursioncount -= 1 # если выходим из рекурсии, глубина -= 1
            return 

    def crawl(self, n=10, ext='bin'):
        """Внешняя функция-интерфейс. n: количество текстов для краулинга. ext: файлы с каким расширением использовать для дампов"""
        if ext not in {'bin', 'txt'}:
            raise UnknownFileExtension('Я не умею записывать такие файлы')
        self.ext = ext
        print('Crawling started')
        self._crawl(self.mainpage, n)  # уходим во внутреннюю рекурсивную функцию
        if self.texts:
            self.writetexts(f'part_{self.writecount}.{self.ext}') # когда рекурсия завершится, запишем оставшийся хвост
        pickle.dump(self.viewed, open('viewedlinks.bin', 'wb'))  # запишем в бинарном формате множество просмотренных ссылок


    def writetexts(self, path):
        """Простенькая запись результата: зависит от того, какое расширение в пути мы укажем"""
        if path.endswith('bin'):
            pickle.dump(self.texts, open(path, 'wb'))
        elif path.endswith('txt'):
            with open(path, 'w', encoding='utf8') as file:
                for text in self.texts:
                    print(text.author, text.title, text.year, text.text, sep='\n', end='\n\n', file=file)