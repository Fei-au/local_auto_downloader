CSV_FILE_PATH = "C:\\Users\\KY\\Desktop\\2026-04-09.csv"
GOOGLE_APPLICATION_CREDENTIALS = "C:\\Users\\KY\\Desktop\\local_auto_downloader\\glass-gasket-415918-b30506c4d63f.json"
TOTAL_SECONDS_PER_ITEM = 20

from datetime import datetime
import logging
import os
import sys
from random import choice
from time import monotonic, sleep
import pandas as pd
from urllib.parse import urlparse
import re
import uuid
import requests
from tempfile import NamedTemporaryFile
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from google.cloud import storage
from google.cloud.sql.connector import Connector, IPTypes
import sqlalchemy
from sqlalchemy import text
import pytz


logger = logging.getLogger('auto_scrapper')
logger.setLevel(logging.INFO)

if not logger.handlers:
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s'))
    logger.addHandler(stream_handler)

logger.propagate = False

INSTANCE_CONNECTION_NAME = "glass-gasket-415918:us-central1:ruitowh"
SQL_PORT=3306
SQL_USER="root"
SQL_PASSWORD="root"
SQL_DATABASE_NAME="ruito"

USE_MS = False
IS_DeVELOPMENT = True
BUCKET = 'rt-staff-files'

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS

connector = Connector()
driver = None


def create_driver():

    if USE_MS:
        options = webdriver.EdgeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument("--disable-dev-shm-usage")
    else:
        options = webdriver.ChromeOptions()

    if IS_DeVELOPMENT:
        options.add_argument('--disable-gpu')  # applicable to windows os only
    else:
        options.add_argument('--headless=new') # Use '--headless=new' for modern versions

    if not USE_MS:
        driver = webdriver.Chrome(service=ChromeService(), options=options)
    else:
        driver = webdriver.Edge(service=EdgeService(), options=options)
    return driver


def ensure_driver():
    global driver
    if driver is None:
        driver = create_driver()
    return driver


def get_image_urls(driver, url):
    # driver.implicitly_wait(10)
    if url[25:-1].isnumeric():
        image_element = driver.find_element(By.ID, 'landingImage')
        return [image_element.get_attribute('src')]
    else:

        try:
            # in case there is a verify code, click the change new code, it will go to the product page.
            try:
                diff_img_button = driver.find_element(By.XPATH, "//a[@onclick='window.location.reload()']")
                diff_img_button.click()
                wait = WebDriverWait(driver, 60)
                wait.until(EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, 'li.a-spacing-small.item.imageThumbnail.a-declarative')))
            except:
                print('do nothing')
            # Find the thumbnail elements with class name "a-spacing-small item imageThumbnail a-declarative"
            thumbnail_elements = driver.find_elements(By.CSS_SELECTOR,
                                                      'li.a-spacing-small.item.imageThumbnail.a-declarative')

            # Interact with each thumbnail element and click the nested <span> with class name
            # "a-button a-button-thumbnail a-button-toggle"
            for i, thumbnail in enumerate(thumbnail_elements[:3], start=1):
                span_element = thumbnail.find_element(By.CSS_SELECTOR,
                                                      'span.a-button.a-button-thumbnail.a-button-toggle')
                ActionChains(driver).move_to_element(span_element).click().perform()
            # logger.info('click each next image')

            # Use explicit wait to wait for the <li> elements with class prefix "image item item" to be present
            li_elements = []
            try:
                wait = WebDriverWait(driver, 10)
                li_elements = wait.until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'li[class^="image item item"]')))
            except TimeoutException:
                print("The elements did not load within the timeout period.")
            image_urls = []

            # Loop through the <li> elements and extract the image URLs
            for i, li_element in enumerate(li_elements[:3], start=1):
                image_element = li_element.find_element(By.TAG_NAME, 'img')
                image_url = image_element.get_attribute('src')
                image_urls.append(image_url)
            # Output the image URLs
            for idx, iURL in enumerate(image_urls, start=1):
                print(f"Image {idx}: {iURL}")
            return image_urls
        except Exception as e:
            logger.error(f'download img error: {e}')



# bypass verify code and wait to find target element
def bypass_verify_code(driver, selector, value):
    try:
        # Click "Continue shopping" on Amazon captcha/checkpoint page when present.
        continue_button_selectors = [
            (By.CSS_SELECTOR, "form[action*='validateCaptcha'] button.a-button-text[type='submit']"),
            (By.XPATH, "//form[contains(@action,'validateCaptcha')]//button[normalize-space()='Continue shopping']"),
            (By.XPATH, "//button[@type='submit' and contains(@alt,'Continue shopping')]"),
        ]

        clicked = False
        for by, locator in continue_button_selectors:
            elements = driver.find_elements(by, locator)
            for element in elements:
                if element.is_displayed() and element.is_enabled():
                    element.click()
                    clicked = True
                    break
            if clicked:
                break
    except Exception:
        # no verify code, just keep going
        pass
    
    try:
        wait = WebDriverWait(driver, 5)
        wait.until(EC.presence_of_all_elements_located((selector, value)))
    except TimeoutException:
        raise TimeoutException(f'element {value} not found')

def get_title(soup):
    span = soup.find('span', id='productTitle')
    if span:
        return span.text.replace('\n', '').strip()
    meta = soup.find('meta', attrs={'name': 'title'})
    if meta:
        return meta['content']
    meta2 = soup.find('meta', attrs={'name': 'description'})
    if meta2:
        return meta2['content']
    title = soup.find('title')
    if title:
        return title.text.replace('\n', '').strip()
    div = soup.find('titleSection')
    if div:
        h1 = div.find('h1', id='title')
        if h1:
            span_with_class = h1.find('span', class_='product-title-word-break')
            if span_with_class:
                return span_with_class.text.replace('\n', '').strip()
    return None


def get_description(soup):
    div = soup.find('div', id='productDescription')
    if div:
        p = div.find('p')
        if p:
            spans = p.find_all('span')
            if spans:
                text = ''
                for s in spans:
                    text += s.text + ' '
                return text
    return None


def get_images_by_script(soup):
    scripts = soup.find_all('script')
    reg = r'"hiRes":"(https?://[^"]+\.jpg)"'
    result = []
    for script in scripts:
        if 'colorImages' in script.text:
            hi_res_urls = re.findall(reg, script.text)
            result += hi_res_urls
            if len(result) >= 3:
                break
    return result[0: 3]

def get_clses(soup):
    a_tags = soup.find_all('a', class_='a-link-normal a-color-tertiary')
    text = None
    if a_tags:
        # if len(a_tags) < 3:
        # for a in a_tags[2:3]:
        if len(a_tags) < 3:
            a = a_tags[0]
        else:
            a = a_tags[2]
            text = a.text.replace('\n', '').strip()
    return text


# def get_size(soup):
#     span_with_id = soup.find('span',id='native_dropdown_selected_size_name')
#     if span_with_id:
#         return  span_with_id.text
#     return  None

def get_mysql_conn():
    conn = connector.connect(
        INSTANCE_CONNECTION_NAME,
        "pymysql",
        user=SQL_USER,
        password=SQL_PASSWORD,
        db=SQL_DATABASE_NAME,
        ip_type=IPTypes.PUBLIC
    )
    return conn

engine = sqlalchemy.create_engine(
    "mysql+pymysql://",
    creator=get_mysql_conn,
)

def insert_temp_item(data):
    with engine.connect() as connection:
        query = text("INSERT INTO inventory_temp_item (title, b_code, lpn_code, upc_ean_code, fnsku_code, msrp_price, category, customize_color, add_date, scrap_date, image1, image2, image3, image1_url, image2_url, image3_url) VALUES (:title, :b_code, :lpn_code, :upc_ean_code, :fnsku_code, :msrp_price, :category, :customize_color, :add_date, :scrap_date, :image1, :image2, :image3, :image1_url, :image2_url, :image3_url)")
        
        connection.execute(query, {
            "title": data['title'],
            "b_code": data['b_code'],
            "lpn_code": data['lpn_code'],
            "upc_ean_code": data['upc_ean_code'],
            "fnsku_code": data['fnsku_code'],
            "msrp_price": data['msrp_price'],
            "category": data['category'],
            "customize_color": data['customize_color'],
            "add_date": data['add_date'],
            "scrap_date": data['scrap_date'],
            "image1": data['image1'],
            "image2": data['image2'],
            "image3": data['image3'],
            "image1_url": data['image1_url'],
            "image2_url": data['image2_url'],
            "image3_url": data['image3_url']
        })
        
        connection.commit()


def fetch_last_week_b_codes():
    query = text("""
        SELECT DISTINCT b_code
        FROM inventory_temp_item
        WHERE b_code IS NOT NULL
          AND add_date >= DATE_SUB(NOW(), INTERVAL 7 DAY)
    """)

    with engine.connect() as connection:
        rows = connection.execute(query).fetchall()

    b_codes = {str(row[0]).strip() for row in rows if row[0]}
    logger.info(f'Fetched {len(b_codes)} B0 codes from last week.')
    return b_codes

def upload_to_gcs(source_file, destination_blob_name):
    """Uploads a file-like object to the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET)
    blob = bucket.blob(destination_blob_name)

    # Upload from the temporary file object
    blob.upload_from_file(source_file, content_type='image/jpeg') 
    
    
def get_extension_from_url(u):
    parsed_url = urlparse(u)
    _, file_extension = os.path.splitext(parsed_url.path)
    return file_extension

def string_to_float_decimal(s):
    # try:
        frm = '{price:.2f}'
        fv = None
        if isinstance(s, float) or isinstance(s,int):
            fv = s
        if isinstance(s,str):
            s = float(s.replace(",", ""))
            fv = float(s)
        result = frm.format(price=fv)
        return float(result)


def normalize_identifier(value):
    if pd.isna(value):
        return None

    if isinstance(value, int):
        return str(value)

    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return str(value).strip()

    text_value = str(value).strip()
    if not text_value:
        return None

    if re.fullmatch(r'\d+\.0+', text_value):
        return text_value.split('.')[0]

    return text_value

def get_color(soup):
    div_with_id = soup.find('div', id='variation_color_name')
    if div_with_id:
        spans = div_with_id.find_all('span', class_='selection')
        if spans:
            return spans[0].text.replace('\n', '').strip()[:30]
    return None


def get_price(soup):
    span = soup.find('span', class_='priceToPay')
    # span = soup.find('span',class_='a-price aok-align-center reinventPricePriceToPayMargin priceToPay')
    if span:
        try:
            s = span.find('span', class_='a-offscreen')
            if s:
                raw = s.text.strip()
                if raw.startswith('$'):
                    t = raw[1:].strip()
                elif raw.startswith('CAD'):
                    t = raw.replace('CAD', '').split('-')[-1].strip()
                else:
                    t = raw
                if t:
                    return string_to_float_decimal(t)
        except Exception as e:
            pass
    spans = soup.find_all('span', class_='apexPriceToPay')
    # For price pattern like $18.30 - $20.55, return highest price
    if spans:
        if len(spans) > 1:
            span = spans[-1]
            s = span.find('span', class_='a-offscreen')
            if s:
                if s.text.startswith('$'):
                    return string_to_float_decimal(s.text[1:])
                elif s.text.startswith('CAD'):
                    return string_to_float_decimal(s.text[3:])
                else:
                    return 0.0
        else:
            span = spans[0].find('span', class_='a-offscreen')
            if span:
                return string_to_float_decimal(span.text[1:])
    parent = soup.find('div', id='desktop_buybox')
    if parent:
        span = parent.find('span', class_='a-price-whole')
        if span:
            return string_to_float_decimal(span.text)
    # span = soup.find('span', id='tp-tool-tip-subtotal-price-value')
    # print('span3', span3)
    # if span3:
    #     s = span3.find('span')
    #     print('return2', s.text)
    #     return string_to_float_decimal(s.text[1:])
    return None


def get_bid_start_price(price):
    try:
        frt = "${:.2f}"
        if price < 6:
            return 1.00
        elif price >= 6 and price <= 10:
            return 2.00
        elif price > 10 and price <= 20:
            return 3.00
        elif price > 20 and price <= 50:
            return 5.00
        elif price > 50 and price <= 100:
            return 10.00
        else:
            v = int(price / 100) * 20
            return string_to_float_decimal(v)
    except:
        return None


# Return status and data if have
# status 0: url not found
# status 1: success
# status 2: url found but something error happended in process the data
# data: only have data for status 1, a dict including title, description ...
# message: status 0 or 2, error message

class TestResponse:
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text


def download_image(image_url):
    if not image_url:
        return None

    extension = get_extension_from_url(image_url) or '.jpg'
    response = requests.get(image_url, timeout=20)
    if response.status_code == 200:
        with NamedTemporaryFile() as img_temp:
            img_temp.write(response.content)
            img_temp.flush()
            img_temp.seek(0)
            # Load the content into a file that can save to Cloud Storage
            # {yyyy-mm-dd}/{uuid.uuid4()}{extension}')
            date_prefix = datetime.now().strftime('%Y%m%d')
            file_path = f'temp_image/{date_prefix}/{uuid.uuid4()}{extension}'
            upload_to_gcs(img_temp, file_path)
            return image_url, file_path
    return None

def scrap(code):
    global driver

    text = None
    us_url = 'https://amazon.ca/dp/' + code + "/"

    driver = ensure_driver()
    driver.get(us_url)
    try:
        bypass_verify_code(driver, By.ID, 'twotabsearchtextbox')
    except TimeoutException as e:
        return {
            'status': 0,
            'message': 'Item not found, it has been removed from Amazon'
        }
    text = driver.page_source
    '''
    user_agent_list = ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36',
                       'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
                       'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36']
    
    accept_language_list = ['en-GB,en;q=0.9,zh-CN;q=0.8,zh;q=0.7,en-AU;q=0.6,en-US;q=0.5',
                            'en',
                            'en;q=0.8,en-GB;q=0.7,en-US;q=0.6']
    
    accept_encoding_list = ['gzip, deflate, br, zsdch, zstd', 'gzip, deflate, br']

    custom_headers = {
        'authority': 'www.amazon.com',
        'pragma': 'no-cache',
        'cache-control': 'no-cache',
        'dnt': '1',
        'upgrade-insecure-requests': '1',
        'sec-fetch-site': 'none',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-dest': 'document',
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "accept-encoding": choice(accept_encoding_list),
        "accept-language": choice(accept_language_list),
        "user-agent": choice(user_agent_list),
    }
    
    response = requests.get(us_url, headers=custom_headers, timeout=30)
    if response.status_code == 200:
        text = response.content.decode('utf-8')
        if "Sorry! We couldn\'t find that page" in text:
            pass
        elif "To discuss automated access to Amazon data" in text:
            raise Exception('Request has been blocked by Amazon')
    elif response.status_code == 404:
        pass
    else:
        raise Exception(f'{response.status_code} + {response.reason}')
    
    if not text:
        ca_url = 'https://amazon.ca/dp/' + code + "/"
        custom_headers['authority'] = 'www.amazon.ca'
        response = requests.get(ca_url, headers=custom_headers, timeout=30)
        if response.status_code == 200:
            text = response.content.decode('utf-8')
            if "Sorry! We couldn\'t find that page" in text:
                pass
            elif "To discuss automated access to Amazon data please contact" in text:
                raise Exception('Request has been blocked by Amazon')
        elif response.status_code == 404:
            pass
        else:
            raise Exception(f'{response.status_code} + {response.reason}')
    
    if not text:
        return {
                    'status': 0,
                    'message': 'Item not found, it has been removed from Amazon'
                }
    '''
    try:
        soup = BeautifulSoup(text, 'html.parser')
        page_text = soup.get_text(" ", strip=True)
        if "Sorry! We couldn't find that page" in page_text:
            return {
                'status': 0,
                'message': 'Item not found, it has been removed from Amazon'
            }

        # urls = get_image_urls(driver, us_url) or []
        # if not urls:
        urls = get_images_by_script(soup)

        images = []
        if urls:
            with ThreadPoolExecutor(max_workers=min(3, len(urls))) as executor:
                futures = executor.map(download_image, urls)
                for result in futures:
                    try:
                        if result:
                            image_url, img_file_path = result
                            images.append((image_url, img_file_path))
                    except Exception as e:
                        logger.error(f'Error downloading image: {e}')
        else:
            return {
                'status': 4,
                'message': "No images found for this item",
            }
        if len(images) == 0:
            images = [(image_url, None) for image_url in urls]
        b_code = code
        title = get_title(soup)
        cls = get_clses(soup)
        customize_color = get_color(soup)
        price = get_price(soup)
        if price is not None:
            price *= 1.4
            price = string_to_float_decimal(price)
        return {
            'status': 1,
            'data': {
                'title': title,
                'b_code': b_code,
                'images': images,
                'category': cls,
                'customize_color': customize_color,
                'msrp_price': price,
            }
        }
    except Exception as e:
        logger.error(f'scrap html error: {e}')
        return {
            'status': -1,
            'message': str(e),
        }
        
        
'''
Status code:
0: url not found
1: success
2: previous scraped url, skipped
3: b code value is empty in the csv
4: image urls not found
-1: exception error when scrap, need to check log for details
'''

def main():
    global driver
    df = pd.read_csv(
        CSV_FILE_PATH,
        dtype={
            'b_code': 'string',
            'lpn_code': 'string',
            'upc_ean_code': 'string',
            'fnsku_code': 'string',
            'detail': 'string',
            'details': 'string',
        }
    )
    tz = pytz.timezone('utc')
    dates = os.path.splitext(os.path.basename(CSV_FILE_PATH))[0].split('-')
    n_str = f'{dates[0]}-{dates[1]}-{dates[2]} 14:00:00.000000'
    add_date=tz.localize(datetime.strptime(n_str, '%Y-%m-%d %H:%M:%S.%f'))

    if 'status' not in df.columns:
        df['status'] = pd.NA
        df.to_csv(CSV_FILE_PATH, index=False)
    if 'details' not in df.columns:
        df['details'] = pd.NA
        df.to_csv(CSV_FILE_PATH, index=False)
    df['details'] = df['details'].astype('string')

    recent_b_codes = fetch_last_week_b_codes()

    success_count = 0
    not_found_count = 0
    failure_count = 0
    skipped_count = 0
    
    try:
        ensure_driver()

        for index, row in df.iterrows():
            row_start_time = monotonic()
            if pd.notna(row['status']) and row['status'] >= 0:
                continue
            current_b_code = str(row['b_code']).strip() if pd.notna(row['b_code']) and str(row['b_code']).startswith('B0') else ''
            if current_b_code in recent_b_codes:
                df.at[index, 'status'] = 2
                df.at[index, 'details'] = ''
                df.to_csv(CSV_FILE_PATH, index=False)
                skipped_count += 1
                continue
            if current_b_code:
                try:
                    result = scrap(code=current_b_code)
                    if result['status'] == 1:
                        data = result['data']
                        data['image1'] = data['images'][0][1] if len(data['images']) > 0 else None
                        data['image2'] = data['images'][1][1] if len(data['images']) > 1 else None
                        data['image3'] = data['images'][2][1] if len(data['images']) > 2 else None
                        data['image1_url'] = data['images'][0][0] if len(data['images']) > 0 else None
                        data['image2_url'] = data['images'][1][0] if len(data['images']) > 1 else None
                        data['image3_url'] = data['images'][2][0] if len(data['images']) > 2 else None
                        data['add_date'] = add_date
                        data['scrap_date'] = datetime.now()
                        data['lpn_code'] = normalize_identifier(row['lpn_code'])
                        data['upc_ean_code'] = normalize_identifier(row['upc_ean_code'])
                        data['fnsku_code'] = normalize_identifier(row['fnsku_code'])
                        insert_temp_item(result['data'])
                        success_count += 1
                    else:
                        not_found_count += 1
                    df.at[index, 'status'] = result['status']
                    df.at[index, 'details'] = ''
                    logger.info(f'{current_b_code} done: {result["status"]}')
                except Exception as e:
                    logger.error(f'scrap error {row["b_code"]}: {e}')
                    df.at[index, 'status'] = -1
                    df.at[index, 'details'] = str(e)
                    failure_count += 1

                finally:
                    df.to_csv(CSV_FILE_PATH, index=False)
                    recent_b_codes.add(current_b_code)
                    elapsed = monotonic() - row_start_time
                    remaining = TOTAL_SECONDS_PER_ITEM - elapsed
                    if remaining > 0:
                        sleep(remaining)
            else:
                df.at[index, 'status'] = 3
                df.at[index, 'details'] = ''
                df.to_csv(CSV_FILE_PATH, index=False)
                skipped_count += 1
            
            if index % 10 == 0:
                logger.info(
                    f'Scraping completed. success={success_count}, failed={failure_count}, not_found={not_found_count}, skipped={skipped_count}'
                )
    finally:
        if driver is not None:
            driver.quit()
            driver = None

                
if __name__ == "__main__":
    main()