from flask import Blueprint, render_template, request, flash
from flask_wtf import FlaskForm
from wtforms import IntegerField, FloatField, SubmitField, validators
from app import db
from datetime import datetime
from ..models.configuration import Configuration

bp = Blueprint('auto_scaling', __name__, template_folder='../templates')


class ConfigForm(FlaskForm):
    grow_threshold = IntegerField(
        'CPU threshold(growing)',
        validators=[
            validators.NumberRange(min=0, max=100, message="Threshold should between (0, 100)")
        ]
    )
    shrink_threshold = IntegerField(
        'CPU threshold(shrinking)',
        validators=[
            validators.NumberRange(min=0, max=100, message="Threshold should between (0, 100)")
        ]
    )
    expand_ratio = FloatField(
        'Expand ratio',
        validators=[
            validators.NumberRange(min=1, max=10, message="Ratio should between [1, 10]")
        ]
    )
    shrink_ratio = FloatField(
        'Shrink ratio',
        validators=[
            validators.NumberRange(min=0, max=1, message="Ratio should between [0, 1]")
        ]
    )
    submit = SubmitField('Update Policy')


@bp.route('/', methods=['GET', 'POST'])
def update_policy():
    form = ConfigForm()
    if request.method == 'GET':
        return render_template('auto_scaling.html', title="EC2 Manager", form=form)
    elif request.method == 'POST':
        if form.validate_on_submit():
            grow_threshold = form.grow_threshold.data
            shrink_threshold = form.shrink_threshold.data
            expand_ratio = form.expand_ratio.data
            shrink_ratio = form.shrink_ratio.data
            if grow_threshold > shrink_threshold:
                config = Configuration(grow_threshold=grow_threshold, shrink_threshold=shrink_threshold,
                                       expand_ratio=expand_ratio, shrink_ratio=shrink_ratio,
                                       create_time=datetime.now())
                db.session.add(config)
                db.session.commit()
                flash("Configuration has been updated!", "success")
            else:
                flash("CPU threshold for growing should not lower than CPU threshold for shrinking", "error")
        else:
            if form.grow_threshold.errors:
                flash("CPU threshold(growing) input invalid", "error")
            elif form.shrink_threshold.errors:
                flash("CPU threshold(shrinking) input invalid", "error")
            elif form.expand_ratio.errors:
                flash("Expand ratio input invalid", "error")
            elif form.shrink_ratio.errors:
                flash("Expand ratio input invalid", "error")
        return render_template("auto_scaling.html", title="EC2 Manager", form=form)
