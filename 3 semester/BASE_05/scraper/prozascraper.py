import re
import os
import pickle
from scraper import Scraper


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
    year = re.search(r'https://proza.ru/(\d{4}/\d\d/\d\d)*', page).group(1) # получаем год с помощью группы
    text = '\n'.join((elem.text for elem in soup.find_all("div", {"class": "text"})))  # собираем все возможные сегменты класса "текст" с помощью bs4
    return author, title, year, text


def main():
    """Стартовая точка: создаем краулер, скрейпим и тут же сохраняем тексты"""
    if os.path.exists('viewedlinks.bin'):
        viewed = pickle.load(open('viewedlinks.bin', 'rb'))
    else:
        viewed = set()
    crawler = Scraper('https://proza.ru/', encoding='cp1251', textre=re.compile(r'https://proza.ru/\d{4}/\d\d/\d\d[/-].*'), attributes=attributes, ndump=200, viewed=viewed)
    crawler.crawl(10, 'txt')

if __name__ == '__main__':
    main()