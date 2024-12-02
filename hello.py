import os
from threading import Thread
from flask import Flask, render_template, session, redirect, url_for
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField
from wtforms.validators import DataRequired
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail, Message

import requests
from datetime import datetime

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hard to guess string'
app.config['SQLALCHEMY_DATABASE_URI'] =\
    'sqlite:///' + os.path.join(basedir, 'data.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['API_KEY'] = os.environ.get('API_KEY')
app.config['API_URL'] = os.environ.get('API_URL')
app.config['API_FROM'] = os.environ.get('API_FROM')

'''
app.config['MAIL_SERVER'] = 'smtp.zoho.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
'''

app.config['FLASKY_MAIL_SUBJECT_PREFIX'] = '[Flasky]'
app.config['FLASKY_MAIL_SENDER'] = 'flaskaulas@zohomail.com'
app.config['FLASKY_ADMIN'] = os.environ.get('FLASKY_ADMIN')

bootstrap = Bootstrap(app)
moment = Moment(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
mail = Mail(app)


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __repr__(self):
        return '<Role %r>' % self.name


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    def __repr__(self):
        return '<User %r>' % self.username


def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)


def send_email(to, subject, template, **kwargs):
    msg = Message(app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender=app.config['FLASKY_MAIL_SENDER'], recipients=[to])    
    msg.html = render_template(template + '.html', **kwargs)
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr

def send_simple_message(to, subject, newUser):
    print('Enviando mensagem (POST)...', flush=True)
    print('URL: ' + str(app.config['API_URL']), flush=True)
    print('api: ' + str(app.config['API_KEY']), flush=True)
    print('from: ' + str(app.config['API_FROM']), flush=True)
    print('to: ' + str(to), flush=True)
    print('subject: ' + str(app.config['FLASKY_MAIL_SUBJECT_PREFIX']) + ' ' + subject, flush=True)
    print('text: ' + "Novo usuário cadastrado: " + newUser, flush=True)

    resposta = requests.post(app.config['API_URL'], 
                             auth=("api", app.config['API_KEY']), data={"from": app.config['API_FROM'], 
                                                                        "to": to, 
                                                                        "subject": app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + ' ' + subject, 
                                                                        "text": "Novo usuário cadastrado: " + newUser})
        
    print('Enviando mensagem (Resposta)...' + str(resposta) + ' - ' + datetime.now().strftime("%m/%d/%Y, %H:%M:%S"), flush=True)
    return resposta


class NameForm(FlaskForm):
    name = StringField('Qual é o seu nome?', validators=[DataRequired()])
    email = BooleanField('Deseja enviar e-mail para flaskaulasweb@zohomail.com?')
    submit = SubmitField('Submit')


@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Role=Role)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


@app.route('/', methods=['GET', 'POST'])
def index():
    form = NameForm()
    user_all = User.query.all();
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.name.data).first()
        if user is None:
            user_role = Role.query.filter_by(name='User').first();
            user = User(username=form.name.data, role=user_role);
            db.session.add(user)
            db.session.commit()
            session['known'] = False

            print('Verificando variáveis de ambiente: Server log do PythonAnyWhere', flush=True)
            print('FLASKY_ADMIN: ' + str(app.config['FLASKY_ADMIN']), flush=True)
            print('URL: ' + str(app.config['API_URL']), flush=True)
            print('api: ' + str(app.config['API_KEY']), flush=True)
            print('from: ' + str(app.config['API_FROM']), flush=True)
            print('to: ' + str([app.config['FLASKY_ADMIN'], "flaskaulasweb@zohomail.com"]), flush=True)
            print('subject: ' + str(app.config['FLASKY_MAIL_SUBJECT_PREFIX']), flush=True)
            print('text: ' + "Novo usuário cadastrado: " + form.name.data, flush=True)
            print('Confirmação do e-mail: ' + "Enviar e-mail para flaskaulasweb@zohomail.com? " + str(form.email.data), flush=True)

            if app.config['FLASKY_ADMIN']:
                print('Enviando mensagem...', flush=True)
                destinatarios = [app.config['FLASKY_ADMIN']]
                if form.email.data == True:
                    destinatarios.append("flaskaulasweb@zohomail.com")
                send_simple_message(destinatarios, 'Novo usuário', form.name.data)
                #send_email(app.config['FLASKY_ADMIN'], 'New User', 'mail/new_user', user=user)
                print('Mensagem enviada...', flush=True)
                
        else:
            session['known'] = True
        session['name'] = form.name.data
        return redirect(url_for('index')) # Aciona o método index() novamente, mas agora com o método GET
    return render_template('index.html', form=form, name=session.get('name'),
                           known=session.get('known', False), user_all=user_all)