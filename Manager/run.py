from app import app as application

if __name__ == '__main__':
    app = application
    # app.run(host='0.0.0.0', port='5000', debug=False)
    app.run(debug=True)