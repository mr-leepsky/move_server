#!/usr/bin/env python
# coding: utf-8

import os
import random
import string

from flask import flash, g, jsonify, Markup, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from application import application, avatars, database, hashing, login_manager, models
from forms import AvatarForm, DataForm, LogInForm, PasswordForm, SettingsForm

APPLICATION_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
USER_SALT_LENGTH = models.Users.salt.property.columns[0].type.length


@application.before_request
def before_request():
    g.user = current_user


@application.route('/', methods=['GET'])
def index():
    return redirect(url_for('log_in'))


@application.route('/sign_up', methods=['GET', 'POST'])
def sign_up():
    data_form = DataForm(prefix='df')
    password_form = PasswordForm(prefix='pf')

    data_form.name.render_kw['placeholder'] = 'Enter name'
    data_form.username.render_kw['placeholder'] = 'Enter username'
    data_form.email.render_kw['placeholder'] = 'Enter e-mail'
    password_form.new_password.render_kw['placeholder'] = 'Enter password'
    password_form.confirm_new_password.render_kw['placeholder'] = 'Confirm password'

    if data_form.validate_on_submit():
        name = unicode(data_form.name.data)
        username = unicode(data_form.username.data)
        email = unicode(data_form.email.data)
        salt = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(USER_SALT_LENGTH))
        password = hashing.hash_value(password_form.new_password.data, salt)

        user = models.Users(name, username, email, password, salt)

        database.session.add(user)
        database.session.commit()

        flash(Markup('<strong>Alright ' + str(user.name) + '!</strong> Welcome on board!'), 'success')

        return redirect(url_for('log_in'))

    return render_template('sign_up.html', data_form=data_form, password_form=password_form)


@application.route('/log_in', methods=['GET', 'POST'])
def log_in():
    login_form = LogInForm(prefix='lf')

    login_form.username.render_kw['placeholder'] = 'Enter username'
    login_form.password.render_kw['placeholder'] = 'Enter password'

    if login_form.validate_on_submit():
        username = unicode(login_form.username.data)
        password = login_form.password.data

        user = models.Users.query.filter_by(username=username).first()

        if not user:
            flash(Markup('<strong>Whoops!</strong> The username and password do not match.'), 'danger')
        else:
            if not hashing.check_value(user.password, password, user.salt):
                flash(Markup('<strong>Whoops!</strong> The username and password do not match.'), 'danger')
            elif not login_user(user):
                flash(Markup('<strong>Ugh!</strong> ' + str(user.name) + ', your account is banned.'), 'danger')
            else:
                flash(Markup('<strong>Hello ' + str(g.user.name) + '!</strong> Glad you are back!'), 'success')

                return redirect(request.args.get('next')) if request.args.get('next') \
                    else redirect(url_for('dashboard'))

    return render_template('log_in.html', login_form=login_form)


@application.route('/m_log_in', methods=['POST'])
def m_log_in():
    username = unicode(request.form.get('username'))
    password = request.form.get('password')

    user = models.Users.query.filter_by(username=username).first()

    if not user:
        response = {'success': False,
                    'message': 'Whoops! The username and password do not match.'}
    else:
        if not hashing.check_value(user.password, password, user.salt):
            response = {'success': False,
                        'message': 'Whoops! The username and password do not match.'}
        elif not login_user(user):
            response = {'success': False,
                        'message': 'Ugh! ' + str(user.name) + ', your account is banned.'}
        else:
            response = {'success': True,
                        'message': 'Hello ' + str(g.user.name) + '! Glad you are back!'}

    return jsonify(response)


@application.route('/log_out', methods=['GET'])
@login_required
def log_out():
    logged_name = g.user.name

    logout_user()

    flash(Markup('<strong>Bye, bye ' + str(logged_name) + '!</strong> Come back soon!'), 'success')

    return redirect(url_for('log_in'))


# TODO: DASHBOARD FUNCTIONALITY
@application.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    return render_template('dashboard.html')


@application.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    settings_form = SettingsForm(prefix='sf')

    if settings_form.validate_on_submit():
        classifier = int(settings_form.classifier.data)

        user = models.Users.query.get(g.user.get_id())

        if classifier != user.classifier_id:
            user.classifier_id = classifier

        database.session.commit()

        flash(Markup('<strong>Great!</strong> All settings has been changed successfully!'), 'success')

    settings_form.classifier.data = str(g.user.classifier_id)

    return render_template('settings.html', settings_form=settings_form)


@application.route('/profile', methods=['GET'])
@login_required
def profile():
    return render_template('profile.html')


@application.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    data_form = DataForm(prefix='df')
    password_form = PasswordForm(prefix='pf')
    avatar_form = AvatarForm(prefix='af')

    data_form.name.render_kw['placeholder'] = str(g.user.name)
    data_form.username.render_kw['placeholder'] = str(g.user.username)
    data_form.email.render_kw['placeholder'] = str(g.user.email)
    password_form.old_password.render_kw['placeholder'] = 'Enter old password'
    password_form.new_password.render_kw['placeholder'] = 'Enter new password'
    password_form.confirm_new_password.render_kw['placeholder'] = 'Confirm new password'

    if data_form.validate_on_submit():
        name = unicode(data_form.name.data)
        username = unicode(data_form.username.data)
        email = unicode(data_form.email.data)

        user = models.Users.query.get(g.user.get_id())

        if name and name != user.name:
            user.name = name

        if username and username != user.username:
            user.username = username

        if email and email != user.email:
            user.email = email

        database.session.commit()

        flash(Markup('<strong>Yahoo!</strong> All data has been changed successfully!'), 'success')

        return redirect(url_for('profile'))

    elif password_form.validate_on_submit():
        new_password = password_form.new_password.data

        user = models.Users.query.get(g.user.get_id())

        if new_password:
            user.salt = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(USER_SALT_LENGTH))
            user.password = hashing.hash_value(new_password, user.salt)

        database.session.commit()

        flash(Markup('<strong>Yeah!</strong> Password has been changed successfully!'), 'success')

        return redirect(url_for('profile'))

    elif avatar_form.validate_on_submit():
        if 'af-avatar' in request.files \
                and avatars.extension_allowed(request.files['af-avatar'].filename.rsplit('.', 1)[1]):
            avatar_path = APPLICATION_DIRECTORY + \
                          url_for('static', filename='images/avatars/' + str(g.user.get_id()) + '.png')

            if os.path.isfile(avatar_path):
                os.remove(avatar_path)

            avatars.save(request.files['af-avatar'], name=str(g.user.get_id()) + '.png')

            flash(Markup('<strong>Nice!</strong> Avatar has been changed successfully! '
                         'If avatar does not change, please refresh the page.'), 'success')

            return redirect(url_for('profile'))
        else:
            flash(Markup('<strong>Ehhh!</strong> Extension of the avatar is not allowed.'), 'danger')

            return redirect(url_for('profile'))

    return render_template('edit_profile.html', data_form=data_form, password_form=password_form,
                           avatar_form=avatar_form)


@application.route('/validate', methods=['GET'])
def validate():
    if g.user.get_id() is None:
        if models.Users.query.filter_by(username=unicode(request.args.get('username'))).first():
            return redirect(url_for('sign_up')), 406

        if models.Users.query.filter_by(email=unicode(request.args.get('email'))).first():
            return redirect(url_for('sign_up')), 406

        return redirect(url_for('sign_up')), 200
    else:
        if unicode(request.args.get('username')) != g.user.username \
                and models.Users.query.filter_by(username=unicode(request.args.get('username'))).first():
            return redirect(url_for('edit_profile')), 406

        if unicode(request.args.get('email')) != g.user.email \
                and models.Users.query.filter_by(email=unicode(request.args.get('email'))).first():
            return redirect(url_for('edit_profile')), 406

        if request.args.get('old_password') \
                and not hashing.check_value(g.user.password, request.args.get('old_password'), g.user.salt):
            print 'password'
            return redirect(url_for('edit_profile')), 406

        return redirect(url_for('edit_profile')), 200


@login_manager.user_loader
def user_loader(id):
    return models.Users.query.get(id)