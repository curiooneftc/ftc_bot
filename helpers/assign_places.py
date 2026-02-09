def assign_places(rows, value_key):
    place = 0
    last_value = None
    for i, row in enumerate(rows):
        value = row[value_key]
        if value != last_value:
            place = i + 1
            last_value = value
        row["place"] = place