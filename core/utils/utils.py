def safe_get_text(element, subtag=None, default=None):
    try:
        if subtag:
            return element.find(subtag).text if element.find(subtag) else default
        return element.text if element else default
    except:
        return default
