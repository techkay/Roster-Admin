from flask import Flask, request
from flask_cors import CORS
from flask_restful import Resource, Api
import datetime
import pickle

monthdays = {30: [9, 4, 6, 11], 28: [2, ], 31: [1, 3, 5, 7, 8, 10, 12]}
year = datetime.datetime.now().year
last_order_index = 6


def is_leap(month):
    if (year % 4 == 0 and year % 100 != 0 or year % 400 == 0):
        return True
    else:
        return False


def get_days(month):
    if (month == 2 and is_leap(month)):
        return 29
    else:
        for key, values in monthdays.items():
            if month in values:
                return key


orderings = [
    ['1A', '1B', '2A', '2B', '3', 'OA', 'OB'],
    ['2A', '2B', '3', 'OA', 'OB', '1A', '1B'],
    ['3', 'OA', 'OB', '1A', '1B', '2A', '2B'],
    ['OA', 'OB', '1A', '1B', '2A', '2B', '3'],
    ['2B', '3', 'OA', 'OB', '1A', '1B', '2A'],
    ['1B', '2A', '2B', '3', 'OA', 'OB', '1A'],
    ['OB', '1A', '1B', '2A', '2B', '3', 'OA']
]


def next(index):
    if (index < 6):
        return index + 1
    else:
        return 0


def prev(index):
    if (index == 0):
        return 6
    else:
        return index - 1


def collectLike(pair):
    shifts = {1: [], 2: [], 3: [], 'OFF': []}
    for group, shift in pair.items():
        if (shift.startswith('1')):
            shifts[1].append(group)
        elif (shift.startswith('2')):
            shifts[2].append(group)
        elif (shift == '3'):
            shifts[3].append(group)
        elif (shift.startswith('O')):
            shifts['OFF'].append(group)
    return shifts


def getGroupandShift(index):
    index = next(index)
    pair = {}
    for e in orderings:
        pair[orderings.index(e) + 1] = e[index]
        # print(pair)
    return collectLike(pair)


def populate_month(month):
    roster = pickle.load(open('roster.pk', 'rb'))
    global last_order_index
    if (month in roster):
        print('accessed from pickle')
        return roster[month]
    else:
        if (month - 1 in roster):
            last_order_index = roster[month - 1]['last_index']
        print('generating')
        month_roster = {}
        for day in range(1, get_days(month) + 1):
            # print(f'Day {day}')
            month_roster[day] = getGroupandShift(last_order_index)
            last_order_index = next(last_order_index)
        month_roster['last_index'] = last_order_index
        roster[month] = month_roster
        pickle.dump(roster, open('roster.pk', 'wb'))
        return month_roster


app = Flask(__name__)
CORS(app)
api = Api(app)


class GenerateRoster(Resource):
    def get(self, month):
        return {'month': populate_month(month)}

    '''
    def put(self, todo_id):
        todos[todo_id] = request.form['data']
        return {todo_id: todos[todo_id]}
    '''


api.add_resource(GenerateRoster, '/<int:month>')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)


