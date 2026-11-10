# Doctrine

Our house rules for agentic development.

Inherits Pullboard standard doctrine version 1.

## W · Writing

## C · Code

## T · Tests

## P · Git and the gate

## D · Dependencies

## S · Security and data

## RG · Rigor proposals
- RG20411 [draft, aim] Review how to prevent repeated "refusal:TEST_FAILURE" (#23, #161). No remedy or red/green proof has been established. Source: rigor-auto:%7B%22version%22%3A1%2C%22unproved%22%3Atrue%2C%22key%22%3A%22refusal%3ATEST_FAILURE%22%2C%22evidence%22%3A%7B%22items%22%3A%5B%7B%22id%22%3A23%2C%22commits%22%3A%5B%22c4d26d79d1d2bf1a873225b0e6cd12282679811f%22%5D%7D%2C%7B%22id%22%3A161%2C%22commits%22%3A%5B%2240322836332614dc94e23ef6b5b29d10b6dcc945%22%5D%7D%5D%2C%22occurrences%22%3A2%2C%22neverAgain%22%3Afalse%2C%22events%22%3A%5B545%2C2041%5D%7D%7D | gate: review
- RG20811 [draft, aim] Review how to prevent repeated "refusal:REOPENED" (#161, #162). No remedy or red/green proof has been established. Source: rigor-auto:%7B%22version%22%3A1%2C%22unproved%22%3Atrue%2C%22key%22%3A%22refusal%3AREOPENED%22%2C%22evidence%22%3A%7B%22items%22%3A%5B%7B%22id%22%3A161%2C%22commits%22%3A%5B%22480c72de04714b3ee578d53cce6b84181371d314%22%5D%7D%2C%7B%22id%22%3A162%2C%22commits%22%3A%5B%222bba301640f3520c707754b76e6a00c81d3aae83%22%5D%7D%5D%2C%22occurrences%22%3A2%2C%22neverAgain%22%3Afalse%2C%22events%22%3A%5B2033%2C2081%5D%7D%7D | gate: review
- RG25591 [draft, aim] Consider splitting "bewerbungen/search_plan.py" into independently owned modules (for example, one module per command). It caused 2 conflict reopens and 0 conflict holds across items #183, #184 in 14 days; review the architecture before deciding. Source: rigor-auto:%7B%22version%22%3A1%2C%22unproved%22%3Atrue%2C%22key%22%3A%22conflict%3Abewerbungen%2Fsearch_plan.py%22%2C%22evidence%22%3A%7B%22items%22%3A%5B%7B%22id%22%3A183%2C%22commits%22%3A%5B%5D%7D%2C%7B%22id%22%3A184%2C%22commits%22%3A%5B%5D%7D%5D%2C%22occurrences%22%3A2%2C%22neverAgain%22%3Afalse%2C%22events%22%3A%5B2487%2C2559%5D%7D%7D | gate: review
- RG25951 [draft, aim] Consider splitting "bewerbungen/hits.py" into independently owned modules (for example, one module per command). It caused 2 conflict reopens and 0 conflict holds across items #184, #185 in 14 days; review the architecture before deciding. Source: rigor-auto:%7B%22version%22%3A1%2C%22unproved%22%3Atrue%2C%22key%22%3A%22conflict%3Abewerbungen%2Fhits.py%22%2C%22evidence%22%3A%7B%22items%22%3A%5B%7B%22id%22%3A184%2C%22commits%22%3A%5B%5D%7D%2C%7B%22id%22%3A185%2C%22commits%22%3A%5B%5D%7D%5D%2C%22occurrences%22%3A2%2C%22neverAgain%22%3Afalse%2C%22events%22%3A%5B2559%2C2595%5D%7D%7D | gate: review
- RG25952 [draft, aim] Consider splitting "bewerbungen/routes_search.py" into independently owned modules (for example, one module per command). It caused 2 conflict reopens and 0 conflict holds across items #184, #185 in 14 days; review the architecture before deciding. Source: rigor-auto:%7B%22version%22%3A1%2C%22unproved%22%3Atrue%2C%22key%22%3A%22conflict%3Abewerbungen%2Froutes_search.py%22%2C%22evidence%22%3A%7B%22items%22%3A%5B%7B%22id%22%3A184%2C%22commits%22%3A%5B%5D%7D%2C%7B%22id%22%3A185%2C%22commits%22%3A%5B%5D%7D%5D%2C%22occurrences%22%3A2%2C%22neverAgain%22%3Afalse%2C%22events%22%3A%5B2559%2C2595%5D%7D%7D | gate: review
- RG29111 [draft, aim] Consider splitting "bewerbungen/CLAUDE.md" into independently owned modules (for example, one module per command). It caused 2 conflict reopens and 0 conflict holds across items #184, #190 in 14 days; review the architecture before deciding. Source: rigor-auto:%7B%22version%22%3A1%2C%22unproved%22%3Atrue%2C%22key%22%3A%22conflict%3Abewerbungen%2FCLAUDE.md%22%2C%22evidence%22%3A%7B%22items%22%3A%5B%7B%22id%22%3A184%2C%22commits%22%3A%5B%5D%7D%2C%7B%22id%22%3A190%2C%22commits%22%3A%5B%5D%7D%5D%2C%22occurrences%22%3A2%2C%22neverAgain%22%3Afalse%2C%22events%22%3A%5B2559%2C2911%5D%7D%7D | gate: review
