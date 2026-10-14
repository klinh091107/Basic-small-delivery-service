"""The single source of truth for proposed status names and transitions."""

STATUSES = ("Received", "Packed", "Handed to Courier", "In Transit", "Delivered")
STATUS_TRANSITIONS = {
    status: list(STATUSES[index:index + 2])
    for index, status in enumerate(STATUSES)
}
