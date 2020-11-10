from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, PasswordField, FileField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, URL
from flask_wtf.file import FileField, FileAllowed, FileRequired

from ...settings import ALLOWED_EXTENSIONS


class RegisterForm(FlaskForm):
    username = StringField(
        'Username',
        validators=[
            DataRequired(),
        ]
    )
    password = PasswordField(
        'Password',
        validators=[
            DataRequired(),
        ]
    )
    submit = SubmitField('Register')


class UploadForm(FlaskForm):
    username = StringField(
        'Username',
        validators=[
            DataRequired(),
        ]
    )
    password = StringField(
        'Password',
        validators=[
            DataRequired(),
        ]
    )
    photo = FileField(
        'Photo to upload', 
        validators=[
            FileRequired(), 
            FileAllowed(ALLOWED_EXTENSIONS)
        ]
    )
    submit = SubmitField('Upload')
