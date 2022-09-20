from flask import Flask, render_template, url_for, request, redirect, make_response
from io import BytesIO
from matplotlib import pyplot
import uuid
import json
import os
import time
import numpy
import base64

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

    def drawPie(self, statistic_data):
        sizes = []
        labels = []
        explode = []
        if os.name == 'nt':
            pyplot.rcParams['font.sans-serif']=['SimHei','SimSun']
        if os.name == 'posix':
            pyplot.rcParams['font-sans-serif']=['Noto Sans CJK SC']
        statistic_dict = statistic_data['statistic_dict']
        sorted_result = sorted(statistic_dict.items(), key=lambda item:item[1], reverse=True)
        sorted_keys = []
        for index in range(len(sorted_result)):
            sorted_keys.append(sorted_result[index][0])
        for key in sorted_keys:
            if len(labels) >= 8 and '其它' not in labels:
                labels.append('其它')
                sizes.append(statistic_dict[key])
                explode.append(0.005)
            elif len(labels) >= 8 and '其它' in labels:
                sizes[-1] = sizes[-1] + statistic_dict[key]
            elif len(labels) < 8:
                labels.append(key)
                sizes.append(statistic_dict[key])
                explode.append(0.005)
            
            
        image_file = BytesIO()
        pyplot.figure(figsize=(9,5),dpi=120)
        pyplot.pie(sizes,
        labels=labels,
        labeldistance=1,
        shadow=False,
        pctdistance=0.5,
        autopct='%.1f%%',
        explode=explode,
        radius=1.4)
        pyplot.savefig(image_file, format='png')
        image_file.seek(0)     
        image_file_base64 = str(base64.b64encode(image_file.getvalue()), 'utf-8')
        return image_file_base64

    def statistic(self, keyword, sender_list, source_list, statistics_type):
        filtered_chat_log = self.filter(keyword, sender_list, source_list)
        statistic_data = {'statistic_dict': {}}
        statistic_dict = statistic_data['statistic_dict']
        for m in filtered_chat_log:
            if statistics_type == 'sender':
                key = m['Sender']
            elif statistics_type == 'source':
                key = m['Source']
            if key not in statistic_dict:
                statistic_dict[key] = 1
            else:
                statistic_dict[key] += 1

        statistic_data['statistic_sender_list'] = sender_list
        statistic_data['statistic_source_list'] = source_list
        statistic_data['statistic_keyword'] = keyword
        statistic_data['statistic_total_number'] = len(filtered_chat_log)
        statistic_data['statistic_pie_base64'] = self.drawPie(statistic_data)
        return statistic_data


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.template_filter('ctime')
def timectime(s):
    return time.ctime(s // 1000)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        if 'file_uuid' in request.cookies:
            file_uuid = request.cookies.get('file_uuid')
            filename = os.path.join(app.config['UPLOAD_FOLDER'],
                                    file_uuid + '.json')
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    chat_log = json.load(f)
                chat_log = MinecraftChatLog(chat_log)
                return render_template('filter.html',
                                       chat_log=chat_log,
                                       show_import=True)
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
        statistics_type = request.json['statistics_type']
        file_uuid = request.cookies.get('file_uuid')
        with open(
                os.path.join(app.config['UPLOAD_FOLDER'],
                             file_uuid + '.json')) as f:
            chat_log = json.load(f)
        chat_log = MinecraftChatLog(chat_log)
        if statistics_type is None:
            filtered_chat_log = chat_log.filter(keyword, sender_list,
                                                source_list)
            return render_template('data.html', data=filtered_chat_log)
        else:
            statistic_data = chat_log.statistic(keyword, sender_list,
                                                source_list, statistics_type)
            return render_template('statistics.html',
                                   data=statistic_data)
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
    app.debug = True
    app.run()
