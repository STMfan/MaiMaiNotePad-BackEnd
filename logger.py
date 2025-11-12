import datetime


def colorize(text, color, style):
    colors = {
        'red': '\033[31m',
        'green': '\033[32m',
        'yellow': '\033[33m',
        'blue': '\033[34m',
        'magenta': '\033[35m',
        'cyan': '\033[36m',
        'white': '\033[37m',
        'grey': '\033[90m',  # 添加grey颜色定义
    }
    styles = {
        'bold': '\033[1m',
        'underline': '\033[4m',
        'blink': '\033[5m',
        'normal': ''
    }
    return f'{styles.get(style, "")}{colors.get(color, "")}{text}\033[0m'


def log(text, importance='debug'):
    if importance == 'debug':
        color = 'grey'
        style = 'normal'
    elif importance == 'info':
        color = 'green'
        style = 'normal'
    elif importance == 'error':
        color = 'red'
        style = 'bold'
    else:
        color = 'red'
        style = 'blink'
    print(f'{colorize(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "blue", "bold")} {colorize(text, color, style)}')
