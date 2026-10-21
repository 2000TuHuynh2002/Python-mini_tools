#!/usr/bin/env python3

import yagmail
import time
import os
import dotenv
from pathlib import Path
import glob



class Email_Sender:
    def __init__(self, sender_email, sender_name, password, delay=2):
        self.__sender_email = sender_email
        self.__sender_name = sender_name
        self.__password = password
        self.__delay = delay
        
        self.__receiver_email_list = []
        self.__subject = "Subject"
        self.__content = ""
        self.__attachment = []
        
        self.__path = os.path.dirname(os.path.abspath(__file__))
        for file in glob.glob(os.path.join(str(self.__path), "attachments/*")):
            self.__attachment.append(file)

    
    def set_receiver_email(self, receiver_email_list: list):
        self.__receiver_email_list = receiver_email_list

    
    def set_mail(self, subject: str, content: str):
        self.__subject = subject
        self.__content = content


    def send_email(self):
        yag = yagmail.SMTP(user={self.__sender_email: self.__sender_name}, password=self.__password)
        if self.__receiver_email_list == [""]:
            print("No receiver email!")
        else:
            for receiver_email in self.__receiver_email_list:
                yag.send(
                    to=receiver_email, 
                    subject=self.__subject, 
                    contents=self.__content, 
                    attachments=self.__attachment
                )
                time.sleep(self.__delay)
            print("Email sent successfully!")
    

def main():
    env_path = dotenv.find_dotenv()
    dotenv.load_dotenv(env_path)
    
    sender_email = os.getenv("SENDER_EMAIL")
    sender_name = os.getenv("SENDER_NAME")
    password = os.getenv("PASSWORD")
    
    subject = "Test"
    content = """
        Hello, this is my test bot.
    """
    with open("./contacts.csv", "r") as f:
        receiver_email_list = f.read().split("\n")
        # print(receiver_email_list)
    
    email_bot = Email_Sender(sender_email, sender_name, password)
    email_bot.set_mail(subject=subject, content=content)
    email_bot.set_receiver_email(receiver_email_list)
    email_bot.send_email()
    

if __name__ == '__main__':
    main()