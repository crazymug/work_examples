def form_search_string(request):
    search_string = request.form['search_string']
    if len(search_string) == 0:
        search_string = '%%'
    return search_string
