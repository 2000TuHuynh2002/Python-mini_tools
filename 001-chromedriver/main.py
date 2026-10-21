#!/usr/bin/env python3

from selenium import webdriver
from selenium.webdriver.chrome.service import Service



def get_driver():
    # Path to chromedriver
    service = Service('') 

    ## Set options for Chrome
    options = webdriver.ChromeOptions()
    options.add_argument('disable-infobars')
    options.add_argument('disable-dev-shm-usage')
    options.add_argument('ignore-certificate-errors')
    options.add_argument('no-sandbox')
    options.add_argument('disable-blink-features=AutomationControlled')
    options.add_argument('start-maximized')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])

    driver = webdriver.Chrome(service=service, options=options)
    return driver


def main():
    driver = get_driver()
    driver.get("https://www.google.com")
   

if __name__ == '__main__':
    main()