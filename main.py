import xml.etree.ElementTree as ET
import datetime
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Company, Phone


def get_companies_from_xml(companies_file):
    """
    Парсит XML файл и возвращает список словарей, где каждый словарь
    представляет компанию.

    Args:
        companies_file (str): Путь к XML файлу.

    Returns:
        list: Список словарей. Каждый словарь содержит данные о компании,
            где ключи — имена тегов XML, а значения — соответствующие
            текстовые данные. Возвращает пустой список, если файл не найден
            или пуст.
    """
    tree = ET.parse(companies_file)
    root = tree.getroot()
    company_list = []

    for elem in root:
        sub_elements = {}
        for sub_elem in elem:
            if sub_elem.tag == 'Телефон':
                if 'Телефон' not in sub_elements:
                    sub_elements['Телефон'] = []
                sub_elements['Телефон'].append(sub_elem.text.strip())
            else:
                sub_elements[sub_elem.tag] = sub_elem.text.strip()
        company_list.append(sub_elements)

    return company_list


def is_valid_field(value, key, num_digits=None):
    """
    Проверяет корректность поля.

    Args:
        value (str): Значение поля.
        key (str): Ключ поля.
        num_digits (int): Ожидаемое количество цифр в поле (если применимо).

    Returns:
        bool: True, если поле корректно, False иначе.
    """
    if value is None:
        logging.warning(f'Обязательное поле "{key}" отсутствует.')
        return False
    elif num_digits and (len(value) != num_digits or not value.isdigit()):
        logging.warning(
            f'Поле "{key}" ({value}) должно состоять из {num_digits} цифр.'
        )
        return False
    else:
        return True


def validate_companies(companies):
    """
    Возвращает список компаний, у которых данные корректны.

    Args:
        companies (list): Список словарей, представляющих компании.

    Returns:
        list: Список валидных компаний.
    """
    valid_companies = []

    for company in companies:
        ogrn = company.get('ОГРН')
        inn = company.get('ИНН')
        data = company.get('ДатаОбн')

        all_valid = [
            is_valid_field(ogrn, 'ОГРН', 13),
            is_valid_field(inn, 'ИНН', 10),
            is_valid_field(data, 'ДатаОбн')
        ]

        if all(all_valid):
            valid_companies.append(company)

    return valid_companies


def remove_duplicates(companies):
    """
    Удаляет дубликаты компаний из списка, оставляя самую новую запись по ОГРН.

    Args:
        companies (list): Список словарей, представляющих компании.

    Returns:
        list: Список компаний без дубликатов.
    """
    grouped_companies = {}
    unique_companies = []

    for company in companies:
        ogrn = company.get('ОГРН')
        if ogrn not in grouped_companies:
            grouped_companies[ogrn] = []
        grouped_companies[ogrn].append(company)

    for key, value in grouped_companies.items():
        if len(value) > 1:
            logging.warning(f'Найдены повторяющиеся записи с ОГРН {key}')
        newest_entry = max(
            value, key=lambda x: datetime.date.fromisoformat(x['ДатаОбн'])
        )
        unique_companies.append(newest_entry)

    return unique_companies


def add_records():
    user = 'superuser'
    password = '1234'
    host = 'localhost'
    port = 5432
    name_db = 'company_from_xml'
    DATABASE_URL = f'postgresql://{user}:{password}@{host}:{port}/{name_db}'

    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        for item_company in unique_companies:
            company = Company(
                ogrn=item_company.get('ОГРН'),
                inn=item_company.get('ИНН'),
                name=item_company.get('НазваниеКомпании'),
                update=datetime.date.fromisoformat(
                    item_company.get('ДатаОбн')
                )
            )
            for item_phone in item_company.get('Телефон'):
                phone = Phone(phone=item_phone, company=company)
                company.phone.append(phone)
            session.add(company)
        session.commit()
        print('Данные успешно добавлены!')
    except Exception as e:
        logging.error(e)
        session.rollback()
    finally:
        session.close()


companies = get_companies_from_xml('companies.xml')
valid_companies = validate_companies(companies)
unique_companies = remove_duplicates(valid_companies)

print(f'Число невалидных компаний: {len(companies) - len(unique_companies)}')
yes_no = input(
    f'Дублирующиеся компании, у которых дата обновления записи '
    f'более старая, и компании, у которых невалидные данные, '
    f'будут отброшены при записи в БД. '
    f'Вы хотите продолжить? (y/n) \n'
)
if yes_no == 'y':
    add_records()
