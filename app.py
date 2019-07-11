#!venv/bin/python
import os
from flask import Flask, request
from flask_cors import CORS
from flask_restful import Resource, Api
import datetime
import pickle
import pymysql
from flask import Flask, Response, url_for, redirect, render_template, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_security import Security, SQLAlchemyUserDatastore, \
    UserMixin, RoleMixin, login_required, current_user
from flask_security.utils import encrypt_password
import flask_admin
from flask_admin.contrib import sqla
from flask_admin import helpers as admin_helpers
from flask_admin import BaseView, expose


#connection = pymysql.connect(host='localhost' , user='root', password='reloaded', db='rosterapp')
#cursor=connection.cursor()

#sqlQuery = """  CREATE TABLE new_users(id SERIAL PRIMARY KEY, Username char(32), Email char(32),Password char(200))"""
    # Execute the sqlQuery
#cursor.execute(sqlQuery)

#connection.close()

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

# Create Flask application
app = Flask(__name__, static_url_path='')
app.config.from_pyfile('config.py')
CORS(app)
api = Api(app)
db = SQLAlchemy(app)


# Define models
roles_users = db.Table(
    'roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    def __str__(self):
        return self.name


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))

    def __str__(self):
        return self.email


# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)


# Create customized model view class
class GenerateRoster(Resource):
    def get(self, month):
        return {'month': populate_month(month)}

api.add_resource(GenerateRoster, '/<int:month>')

class MyModelView(sqla.ModelView):

    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False

        if current_user.has_role('superuser'):
            return True

        return False

    def _handle_view(self, name, **kwargs):
        """
        Override builtin _handle_view in order to redirect users when a view is not accessible.
        """
        if not self.is_accessible():
            if current_user.is_authenticated:
                # permission denied
                abort(403)
            else:
                # login
                return redirect(url_for('security.login', next=request.url))


    # can_edit = True
    edit_modal = True
    create_modal = True    
    can_export = True
    can_view_details = True
    details_modal = True

class UserView(MyModelView):
    column_editable_list = ['email', 'first_name', 'last_name']
    column_searchable_list = column_editable_list
    column_exclude_list = ['password']
    # form_excluded_columns = column_exclude_list
    column_details_exclude_list = column_exclude_list
    column_filters = column_editable_list


#class CustomView(BaseView):
  #  @expose('/')
  #  def index(self):
   #     return self.render('admin/custom_index.html')

class CustomView(BaseView):
    @expose('/')
    def index(self):

        return app.send_static_file('roster.html')



    def roster(self):
        return self.render('admin/roster.html')

# Flask views
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/roster')
def roster():
    return app.send_static_file('roster.html')


# Create admin
admin = flask_admin.Admin(
    app,
    'My Dashboard',
    base_template='my_master.html',
    template_mode='bootstrap3',
)

# Add model views
admin.add_view(MyModelView(Role, db.session, menu_icon_type='fa', menu_icon_value='fa-server', name="Roles"))
admin.add_view(UserView(User, db.session, menu_icon_type='fa', menu_icon_value='fa-users', name="Users"))
admin.add_view(CustomView(name="View Roster", endpoint='custom', menu_icon_type='fa', menu_icon_value='fa-connectdevelop',))

# define a context processor for merging flask-admin's template context into the
# flask-security views.
@security.context_processor
def security_context_processor():
    return dict(
        admin_base_template=admin.base_template,
        admin_view=admin.index_view,
        h=admin_helpers,
        get_url=url_for
    )

def build_sample_db():
    """
    Populate a small db with some example entries.
    """

    import string
    import random

    db.drop_all()
    db.create_all()

    with app.app_context():
        user_role = Role(name='user')
        super_user_role = Role(name='superuser')
        db.session.add(user_role)
        db.session.add(super_user_role)
        db.session.commit()

        test_user = user_datastore.create_user(
            first_name='Admin',
            email='admin',
            password=encrypt_password('admin'),
            roles=[user_role, super_user_role]
        )

        first_names = [
            'Harry', 'Amelia', 'Oliver', 'Jack', 'Isabella', 'Charlie', 'Sophie', 'Mia',
            'Jacob', 'Thomas', 'Emily', 'Lily', 'Ava', 'Isla', 'Alfie', 'Olivia', 'Jessica',
            'Riley', 'William', 'James', 'Geoffrey', 'Lisa', 'Benjamin', 'Stacey', 'Lucy'
        ]
        last_names = [
            'Brown', 'Smith', 'Patel', 'Jones', 'Williams', 'Johnson', 'Taylor', 'Thomas',
            'Roberts', 'Khan', 'Lewis', 'Jackson', 'Clarke', 'James', 'Phillips', 'Wilson',
            'Ali', 'Mason', 'Mitchell', 'Rose', 'Davis', 'Davies', 'Rodriguez', 'Cox', 'Alexander'
        ]

        for i in range(len(first_names)):
            tmp_email = first_names[i].lower() + "." + last_names[i].lower() + "@example.com"
            tmp_pass = ''.join(random.choice(string.ascii_lowercase + string.digits) for i in range(10))
            user_datastore.create_user(
                first_name=first_names[i],
                last_name=last_names[i],
                email=tmp_email,
                password=encrypt_password(tmp_pass),
                roles=[user_role, ]
            )
        db.session.commit()
    return

# define roster function -----------------------------------------------------


if __name__ == '__main__':

    # Build a sample db on the fly, if one does not exist yet.
    app_dir = os.path.realpath(os.path.dirname(__file__))
    database_path = os.path.join(app_dir, app.config['DATABASE_FILE'])
    if not os.path.exists(database_path):
        build_sample_db()

    # Start app
    app.run(debug=True)