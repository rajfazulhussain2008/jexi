import traceback
try:
    import routes.social_routes
except Exception as e:
    with open("err.txt", "w") as f:
        traceback.print_exc(file=f)
