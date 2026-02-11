

def admin_receivers_key(admin_id: int) -> str:
    return f"admin:{admin_id}:receivers"

def admin_chosen_mailing_template_key(admin_id: int) -> str:
    return f"admin{admin_id}:mailing:template"


def user_requestlimit_key(user_id: int) -> str:
    return f"user:{user_id}:requestlimit"