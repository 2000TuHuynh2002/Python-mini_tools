# Email Tool


## Introduction
This is a simple email tool that allows you to send emails using Python.


## Features
- Send emails to one or multiple recipients
- Customize email subject and body
- Attach files to your emails
- Supports HTML content in emails


## Installation
To use this tool, you need to have Python installed on your machine. You can install it by following the instructions on the [Python website](https://www.python.org/downloads/).


## Usage
1. Clone or download the repository to your local machine.

2. Open a terminal or command prompt and navigate to the project directory.
   ```bash
   cd ./2-gmail_bot/
   ```

3. Install the required dependencies by running the following command:
   <br>
   <i>&nbsp;**(If you are using Windows, use <b>pip</b> instead of <b>pip3</b>)&nbsp;</i>

   ```bash
   pip3 install -r ./requirements.txt
   ```

4. Change `.env.example` to `.env`. Update the `.env` file with your email details and your email credentials. (Serch "Gmail app password" for more information). For example:
   ```env
   SENDER_EMAIL="yourEmail@example.com"
   SENDER_NAME="Your Name"
   PASSWORD="xxxx xxxx xxxx xxxx" # 16 character from gmail app password
   ```

5. Update the `contacts.csv` with emails that you want to send.
   For example:
   ```csv
   emailA@example.com
   emailB@example.com
   emailC@example.com
   ```

6. Put every files you want to attach in the `attachments/` folder.

7. Write your Suject and Content in `main.py`. _(If your content is a little bit long, write your content in a new file and modify the code to import it.)_

8. Run the tool by executing the following command:
   <br>
   <i>&nbsp;**(If you are using Windows, use <b>python</b> instead of <b>python3</b>)&nbsp;</i>

   ```bash
   python3 ./main.py
   ```


## Contributing
If you would like to contribute to this project, feel free to fork the repository and submit a pull request. Any contributions are welcome!
