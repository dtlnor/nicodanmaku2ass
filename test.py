import re

with open('a.txt',encoding='utf8') as f:
    lines = f.read().splitlines()

open('result.txt', 'w', encoding='utf8').close()


for l in lines:
    m = re.match(r'(Dialogue.+})(.+?)$', l)
    header = m[1]
    raw_text = m[2].split('\\N')
    s = ''
    h = 0  
    line_height = 9
    for t in raw_text:
        print(t, h)
        s += re.sub(r'(\\move\(\d+, )\d+(, [0-9\-]+, )\d+\)', f'\\g<1>{h}\\g<2>{h})', header) + t + '\n'
        h += line_height
    with open('result.txt', 'a', encoding='utf8') as fo:
        fo.write(s)
