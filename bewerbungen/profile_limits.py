"""The limits of a search profile line, as Meine Angaben sets them for its field in onboarding/form.json (#302).

Suche einstellen and Meine Angaben write the same lines of suchprofil.md. Both take a value only within the limits of
the form field, so what one page saves the other takes in full. The form itself is read by `form_limits.py`.
"""
import form_limits
import search_plan

Limit = form_limits.Limit
SECTIONS = {search_plan.KIND_JOB: form_limits.JOB_SECTION, search_plan.KIND_APPRENTICESHIP: form_limits.APPRENTICESHIP_SECTION}
# Where Suche einstellen adds an own term (#310): a job term joins the Kernliste, and without one it becomes a direction,
# whose field takes longer lines; so the keywords decide.
TERM_FIELDS = {search_plan.KIND_JOB: "keywords", search_plan.KIND_APPRENTICESHIP: "professions"}


def of(kind: str, field_id: str) -> Limit:
    """The limits of a field in the search section of this kind; LookupError if the form has no such field."""
    return form_limits.of(SECTIONS[kind], field_id)


def of_term(kind: str) -> Limit:
    """The limits of a search term the person adds on Suche einstellen, as Meine Angaben takes it (#310)."""
    return of(kind, TERM_FIELDS[kind])
