import imaplib
import email
# from email.header import decode_header
import webbrowser
import os
import getpass
from itertools import repeat
import re
import string
from nltk.corpus import stopwords
import pandas as pd
from tqdm import tqdm
import unidecode
from os.path import exists
from bs4 import BeautifulSoup

import pdb

stop_words = set(stopwords.words('english'))

class natural_text():

    def __init__(self, msg):
        self.msg = msg

    def print_msg(self):
        print(self.msg)

    def clean_str(self, tasks):
    
        if 'unicode' in tasks:
            self.msg = unidecode.unidecode(self.msg)
        if 'punctuation' in tasks:
            self.msg = re.sub(r'[^\w\s]', " " , self.msg)
        if 'numbers' in tasks:
            self.msg = re.sub(r"\w*\d+\w*", " ", self.msg)
        if 'lower_case' in tasks:
            self.msg = "".join([i.lower() for i in self.msg])
        if 'overspace' in tasks:
            self.msg = re.sub(r"\s{2,}", " ", self.msg).strip()
        if 'stopwords' in tasks:
            self.msg = " ".join([i for i in self.msg.split(' ') if i not in stop_words])

def credentials(path):
    
    try:
        with open(path) as f:
            username, password = f.read().splitlines()
    except FileNotFoundError:
        username = input("Enter your email address: ")
        password = getpass.getpass()
    except:
        raise EOFError('Oupsy, it looks like a credential file has been found, '+\
                       'but it is not correctly formatted.')

    return username, password


def extract_html(part):

    soup = BeautifulSoup(part.get_payload(), features="html5lib")

    # kill all script and style elements
    for script in soup(["script", "style"]):
        script.extract()    # rip it out

    content_txt = soup.get_text().replace("=\n", '')

    return content_txt

def get_subject(msg):

    subject = email.header.decode_header(msg["Subject"])

    subject = [s_i.decode(d_i) if d_i != None else
               s_i.decode() if isinstance(s_i, bytes) else
               s_i if isinstance(s_i, str) else
               'nan' for s_i, d_i in subject]

    if 'nan' in subject:
        raise AttributeError('A part of the subject was not bytes or str.')

    return ' '.join(subject)


def get_sender(msg):

    sender = email.header.decode_header(msg.get("From"))

    sender = ' '.join([s_i if isinstance(s_i, str) else
                       s_i.decode(d_i) if (isinstance(s_i, bytes) and d_i != None)  else
                       s_i.decode() if (isinstance(s_i, bytes) and d_i == None) else
                       'nan' for s_i, d_i in sender])
    if 'nan' in sender:
        raise AttributeError('A part of the sender was not bytes or str.')

    if ('<' and '>') in sender:
        sender = re.findall(r".+?(?=<)", sender)
    elif '@' in sender:
        sender = ['no info']
    else:
        raise ValueError('Oupsy, looks like I cannot define the sender.')

    return sender[0]


def get_address(msg):

    address = email.header.decode_header(msg.get("From"))
    address = ' '.join([s_i if isinstance(s_i, str) else
                       s_i.decode(d_i) if (isinstance(s_i, bytes) and d_i != None)  else
                       s_i.decode() if (isinstance(s_i, bytes) and d_i == None) else
                       'nan' for s_i, d_i in address])
    if 'nan' in address:
        raise AttributeError('A part of the address was not bytes or str.')

    if ('<' and '>') in address:
        address = re.findall(r"\<(.*?)\>", address)
    elif '@' in address:
        address = [address]
    else:
        raise ValueError('Oupsy, looks like I cannot define the address.')

    return address[0]


def get_content(msg):

    if msg.is_multipart():
        content = []
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            if content_type == 'text/plain' and "attachment" not in content_disposition:
                content.append(part.get_payload())
            elif (content_type == 'text/html') & (len(content) > 0):
                # Already read the text part, no need for the HTML part
                pass
            elif (content_type == 'text/html'):
                    content.append(extract_html(part))
            elif content_type.startswith('multipart') or content_type.startswith('image') or (content_type == 'text/calendar'):
                pass
            else:
                raise ValueError('content type is not text/plain or contains attachment, or content_type not multipart/alternative')

    elif msg.is_multipart() == False:
        content_type = msg.get_content_type()
        content_disposition = str(msg.get("Content-Disposition"))
        if content_type == 'text/plain' and "attachment" not in content_disposition:
            content = [msg.get_payload()]
        elif content_type == 'text/html':
            content = [extract_html(msg)]
        elif content_type.startswith('image') or (content_type == 'text/calendar'):
            # these sometimes appear in the content: pass
            pass
        else:
            raise ValueError('content type is not text/plain or contains attachment, or content_type not multipart/alternative')

    else:
        raise TypeError('Oupsy, looks like I cannot define the content of the email.')

    return ' '.join(content)

if __name__ == "__main__":

    # Get the credentials for the email.
    username, password = credentials('./.credentials')

    # create an IMAP4 class with SSL 
    imap = imaplib.IMAP4_SSL("imap.laposte.net")
    # authenticate
    imap.login(username, password)

    status, messages = imap.select("INBOX")

    # number of emails to fetch
    N = 500

    # total number of emails
    N_email = int(messages[0])

    # Create an empty dictionary to store the emails into a DB.
    empty_list=[]
    empty_list.extend(repeat(' ',N))
    df = {"id":empty_list.copy(),
          "subject":empty_list.copy(),
          "from":empty_list.copy(),
          "email":empty_list.copy(),
          "content":empty_list.copy()}

    for i in tqdm(range(N)):

        df['id'][i] = i+1

        # fetch the email message by ID
        res, msg = imap.fetch(str(N_email-i), "(RFC822)")

        for response in msg:
            
            if isinstance(response, tuple):

                # parse a bytes email into a message object
                msg = email.message_from_bytes(response[1])

                # decode, clean, and save the email subject
                subject = get_subject(msg)
                subject = natural_text(subject)
                subject.clean_str(['unicode', \
                                   'punctuation', \
                                   'numbers', \
                                   'lower_case', \
                                   'overspace'])
                df['subject'][i] = subject.msg

                # decode, clean, and save the sender
                sender = get_sender(msg)
                sender = natural_text(sender)
                sender.clean_str(['unicode', \
                                  'punctuation',\
                                  'lower_case',\
                                  'overspace'])
                df['from'][i] = sender.msg

                # decode, clean, and save the email address
                df['email'][i] = get_address(msg)

                # decode, clean, and save the content
                content = get_content(msg)
                content = natural_text(content)
                content.clean_str(['unicode', \
                                   'punctuation', \
                                   'numbers', \
                                   'lower_case', \
                                   'overspace', \
                                   'stopwords'])

                df['content'][i] = content.msg
               
            elif isinstance(response, bytes) & (response.decode() == ')'):
                # Sometimes this character comes up in the response => ignored and pass.
                pass
            else:
                raise ValueError('sorry, not coded to handle this type of messages.')

    imap.close()
    imap.logout()

    pd.DataFrame(df).to_csv('./email_data/email.csv', index = False)

