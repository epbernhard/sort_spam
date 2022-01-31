import imaplib
import email
from email.header import decode_header
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

import pdb

stop_words = set(stopwords.words('english'))

class natural_text():

    def __init__(self, msg):
        self.msg = msg

    def unicode_to_ascii(self):
        self.msg = unidecode.unidecode(self.msg)

    def print_msg(self):
        print(self.msg)

    def re_punc(self):
        self.msg = re.sub("[^-9A-Za-z]", " " , self.msg)

    def lower_case(self):
        self.msg = "".join([i.lower () for i in self.msg])

    def re_unicode(self):
        self.msg = self.msg.encode('ascii', 'ignore').decode()

    def re_stopwords(self):
        self.msg = " ".join([i for i in self.msg.split(' ') if i not in stop_words])

    def re_numbers(self):
        self.msg = re.sub(r"\w*\d+\w*", " ", self.msg)

    def re_overspace(self):
        self.msg = re.sub(r"\s{2,}", " ", self.msg)

    def re_oneword(self):
        self.msg = " ".join([i for i in self.msg.split(' ') if len(i) > 1])

    def re_ticks(self):
        self.msg = re.sub(r"\'\w+", " ", self.msg)

    def get_body(self):
        return self.msg


if __name__ == "__main__":

    try:
        username, password = open('./.credentials').read().splitlines()
    except:
        username = input("Enter your email address: ")
        password = getpass.getpass()

    # create an IMAP4 class with SSL 
    imap = imaplib.IMAP4_SSL("imap.laposte.net")
    # authenticate
    imap.login(username, password)

    status, messages = imap.select("INBOX")

    # number of top emails to fetch
    N = 500

    # total number of emails
    N_email = int(messages[0])

    # Dictionary to store the emails
    empty_list=[]
    empty_list.extend(repeat('nan',N))
    df = {"id":empty_list.copy(),
          "subject":empty_list.copy(),
          "from":empty_list.copy(),
          "email":empty_list.copy(),
          "content":empty_list.copy()}

    ind = 0
    for i in tqdm(range(N_email, N_email-N, -1)):

        df['id'][ind] = ind+1

        # fetch the email message by ID
        res, msg = imap.fetch(str(i), "(RFC822)")
        for response in msg:
            if isinstance(response, tuple):

                # parse a bytes email into a message object
                msg = email.message_from_bytes(response[1])

                # decode the email subject
                subject = decode_header(msg["Subject"])
                subject_iii = []
                for subject_i in subject:
                    subject_ii, encoding = subject_i[0], subject_i[1]

                    if isinstance(subject_ii, bytes) and (encoding != None):
                        if subject_ii.decode(encoding) != ' ':
                            subject_iii.append(subject_ii.decode(encoding))
                    elif isinstance(subject_ii, bytes):
                        if subject_ii.decode() != ' ':
                            subject_iii.append(subject_ii.decode())
                    elif isinstance(subject_ii, str):
                        subject_iii.append(subject_ii)
                    else:
                        pdb.set_trace()
                        raise ValueError('The subject is not bytes, or str.')

                subject = natural_text(' '.join(subject_iii))
                subject.unicode_to_ascii()
                # subject.print_msg()

                df['subject'][ind] = subject.msg

                # decode email and sender
                From = decode_header(msg.get("From"))
                if len(From) == 1:
                    from_i, encoding = From[0][0], From[0][1]

                    if from_i.endswith('>'):
                        i = 0
                        from_ii = []
                        while from_i[i] != '<':
                            if from_i[i] not in ['"', '@']:
                                from_ii.append(from_i[i])
                            i += 1
                        df['from'][ind] = ''.join(l for l in from_ii)

                        df['email'][ind] =  re.findall('\<(.*?)\>', from_i)[0]

                    elif isinstance(from_i, str) and ('@' in from_i):
                        df['from'][ind] = re.findall('\@(.*?)\.', from_i)[0]
                        df['email'][ind] = from_i

                    else:
                        raise ValueError('len(From) = 1, and not a string or an email.')

                elif len(From) > 1:
                    if len(From) == 3:
                        From = From[1:]

                    from_i, encoding = From[0][0], From[0][1]
                    if (isinstance(from_i, bytes)) and (encoding != None):
                        from_i = from_i.decode(encoding)
                    else:
                        raise ValueError('from_i is not byte, or encodimg is None.')
                
                    df['from'][ind] = from_i

                    email_i, encoding = From[1][0], From[1][1]
                    if (isinstance(email_i, bytes)) and (encoding != None):
                        email_i = email_i.decode(encoding)
                    elif isinstance(email_i, bytes):
                        email_i = email_i.decode()
                    else:
                        raise ValueError('email is not byte.')

                    df['email'][ind] = re.findall('\<(.*?)\>', email_i)[0]

                # # decode email body
                # # if the email message is multipart
                # body = None
                # if msg.is_multipart():
                #     # iterate over email parts
                #     for part in msg.walk():
                #         # extract content type of email
                #         content_type = part.get_content_type()
                #         content_disposition = str(part.get("Content-Disposition"))
                #         if content_type == 'text/plain' and "attachment" not in content_disposition:
                #             if isinstance(part.get_payload(decode = True), bytes):
                #                 body = part.get_payload()
                #             else:
                #                 body = part.get_payload(decode = True).decode()
                
                # else:
                #     # extract content type of email
                #     content_type = msg.get_content_type()
                #     # get the email body
                #     if content_type == "text/plain":
                #         body = msg.get_payload()
            elif isinstance(response, bytes):
                pass
            else:
                raise ValueError('sorry, not coded to handle this type of messages.')


        # if body == None:
        #     ind += 1
        #     continue

        # # Clean the body
        # content = body_text(body)
        # content.re_punc()
        # content.lower_case()
        # content.re_unicode()
        # content.re_stopwords()
        # content.re_numbers()
        # content.re_overspace()
        # content.re_oneword()
        # content.re_ticks()

        # content.print_msg()
        # print(str(ind) + '--------')
            
        # df['content'][ind] = content.get_body()
        ind += 1

    imap.close()
    imap.logout()

    pd.DataFrame(df).to_csv('./email_data/email.csv', index = False)

