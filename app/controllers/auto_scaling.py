from flask import Blueprint, render_template
from flask import request, flash, redirect, url_for
import boto3


bp = Blueprint('auto_scaling', __name__, template_folder='../templates')


@bp.route('/', methods=['GET'])
def load_current_policy():
    return render_template("auto_scaling.html", title="EC2 Manager")
