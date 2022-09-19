from flask import Flask, render_template, url_for, request, redirect, make_response
import uuid
import json
import os
import time

UPLOAD_FOLDER = 'data'
# UPLOAD_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = set(['json'])
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


class MinecraftChatLog:

    def __init__(self, chat_log):
        self.chat_log = chat_log
        self.sender_list = []
        self.source_list = []
        for m in self.chat_log:
            sender = m['Sender']
            source = m['Source']
            if sender not in self.sender_list:
                self.sender_list.append(sender)
            if source not in self.source_list:
                self.source_list.append(source)

    def filter(self, keyword, sender_list, source_list):
        filtered_chat_log = []
        for m in self.chat_log:
            if m['Sender'] in sender_list and m['Source'] in source_list:
                if keyword in m['Content'] or keyword == '':
                    filtered_chat_log.append(m)
        return filtered_chat_log

    def context(self, message, sender, source, time):
        context = []
        for m in self.chat_log:
            if m['Content'] == message and m['Sender'] == sender and m[
                    'Source'] == source and m['Time'] == time:
                p = self.chat_log.index(m)
                break
        for i in range(p - 30, p + 30):
            if i < 0 or i >= len(self.chat_log):
                continue
            context.append(self.chat_log[i])
        return context


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.template_filter('ctime')
def timectime(s):
    return time.ctime(s // 1000)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template('index.html')
    elif request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            try:
                chat_log = json.load(file)
                chat_log = MinecraftChatLog(chat_log)
                file_uuid = str(uuid.uuid4())
                with open(
                        os.path.join(app.config['UPLOAD_FOLDER'],
                                     file_uuid + '.json'), 'w') as f:
                    json.dump(chat_log.chat_log, f)
                resp = make_response(
                    render_template('filter.html', chat_log=chat_log))
                resp.set_cookie('file_uuid', file_uuid)
                return resp
            except Exception as e:
                return render_template('error.html',
                                       error=f'Invalid JSON: {e}')
        else:
            return render_template('error.html', error='Invalid file type')
    else:
        return redirect(url_for('index'))


@app.route('/static/<path:path>')
def send_static(path):
    return url_for('static', path)


@app.route('/filter', methods=['GET', 'POST'])
def filter():
    if request.method == 'POST':
        keyword = request.json['keyword']
        sender_list = request.json['sender_list']
        source_list = request.json['source_list']
        file_uuid = request.cookies.get('file_uuid')
        with open(
                os.path.join(app.config['UPLOAD_FOLDER'],
                             file_uuid + '.json')) as f:
            chat_log = json.load(f)
            chat_log = MinecraftChatLog(chat_log)
            filtered_chat_log = chat_log.filter(keyword, sender_list,
                                                source_list)
            return render_template('data.html', data=filtered_chat_log)
    else:
        return redirect(url_for('index'))


@app.route('/context', methods=['GET', 'POST'])
def context():
    if request.method == 'POST':
        message = request.json['message']
        sender = request.json['sender']
        source = request.json['source']
        time = request.json['time']
        file_uuid = request.cookies.get('file_uuid')
        with open(
                os.path.join(app.config['UPLOAD_FOLDER'],
                             file_uuid + '.json')) as f:
            chat_log = json.load(f)
            chat_log = MinecraftChatLog(chat_log)
            context = chat_log.context(message, sender, source, time)
            return render_template('data.html', data=context)
    else:
        return redirect(url_for('index'))


if __name__ == '__main__':
    # app.debug = True
    app.run()
