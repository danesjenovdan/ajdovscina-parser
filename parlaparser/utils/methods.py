def get_values(data, key='UNID'):
    if isinstance(data, dict):
        children = data.get(key)
        return get_values(children, key)
    elif isinstance(data, list):
        output = [get_values(item, key) for item in data]
        if not output:
            return []
        if isinstance(output[0], list):
            return [item for sublist in output for item in sublist]
        return output
    elif isinstance(data, str):
        return [data]
