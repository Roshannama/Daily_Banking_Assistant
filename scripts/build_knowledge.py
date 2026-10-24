"""Author fictional policy sources and their approval manifest, not real bank policy."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
POLICIES = [
 ('accounts','Account access and balances',[
 ('access','Account balance and account access require a trusted customer session and PIN verification for each protected request. The chatbot never treats a customer ID typed in chat as authentication.'),
 ('availability','Available account balance comes only from authorized banking tools. If the bank system is unavailable, the assistant reports data unavailable; it does not guess a balance.')]),
 ('payments','UPI and payment failures',[
 ('failed','For a failed UPI payment, check the transaction status and reference in your bank app. Avoid repeating the payment until its status is clear. If your account was debited, contact bank support with the reference. This fictional policy does not promise a refund deadline.'),
 ('pending','A pending UPI payment has not reached a final status. Keep the reference number and check again in the bank app. Contact support if uncertainty persists. Do not assume pending means successful.'),
 ('definition','UPI is a digital payment method used for bank-to-bank payments. Never share your payment PIN or OTP with a caller or in chatbot messages.')]),
 ('cards','Debit and credit card services',[
 ('lost','If a debit or credit card is lost or stolen, request card blocking promptly. This prototype requires the exact card ID, PIN verification and explicit confirmation before blocking. Use your bank emergency channel for urgent real incidents.'),
 ('replacement','For card replacement, contact authorized bank support after protecting the lost card. Replacement fulfillment and fees are not implemented in this demo; no delivery date or fee is promised.')]),
 ('fraud','Fraud and disputes',[
 ('dispute','To open a transaction dispute, identify the exact transaction ID. The transaction must belong to your authenticated customer. PIN verification and explicit confirmation are required. Repeated submissions for the same transaction return the existing dispute.'),
 ('suspicious','For suspicious or unrecognized transactions, review your transaction records and contact bank support promptly. Automated fraud indicators are not a determination of fraud. High-risk investigations require an authorized bank employee.')]),
 ('credit','Credit card billing',[
 ('statement','A credit card statement shows the amount due and payment due date. Retrieve your own card statement using PIN-authorized banking tools. Available repayment methods are shown only when recorded by the bank.'),
 ('minimum','Paying only the minimum credit card amount may leave an outstanding balance. Charges and terms depend on your actual agreement. This fictional demo does not calculate interest or promise a grace period.')]),
 ('loans','Loans and EMI',[
 ('schedule','EMI means equated monthly installment. Your loan schedule contains the EMI amount, next due date and outstanding balance. Personal loan records require PIN verification.'),
 ('hardship','If you cannot pay an EMI, contact authorized bank support to discuss available options. This demo cannot approve restructuring, defer payments or waive fees.')]),
 ('offers','Personalized offers',[
 ('consent','Personalized offer eligibility is retrieved only after PIN verification and recorded consent. The model never decides eligibility. A pre-approved offer still requires the bank final approval and applicable checks.'),
 ('products','General product descriptions are informational. This demo does not recommend specific investments or guarantee returns. For investment suitability advice, speak with an authorized financial adviser who can consider your circumstances.')]),
 ('privacy','Banking privacy and AI safety',[
 ('credentials','Never share a PIN, password, OTP or session token in chat. Enter a requested PIN only in the secure PIN form. PINs must not appear in chat history, model input or audit logs.'),
 ('isolation','A customer may access only their own authorized records. Another customer ID in a prompt does not grant access. Audit logs contain trace IDs and decisions, not raw private messages.')]),
 ('bills','Bill reminders and financial guidance',[
 ('reminders','Upcoming payment reminders include recorded utility bills, subscriptions, credit card dues and EMIs. The demo displays reminders when asked; it does not send scheduled notifications or execute payments.'),
 ('saving','Savings observations use successful income and expense records and upcoming obligations. Failed payments are not counted as settled spending. Remaining funds are an estimate excluding unrecorded future income or expenses. No investment return is guaranteed.')]),
]

def main():
    root=ROOT/'knowledge_base'; (root/'markdown').mkdir(parents=True,exist_ok=True); (root/'metadata').mkdir(exist_ok=True)
    manifest=[]
    for ident,title,sections in POLICIES:
        source=f'markdown/{ident}.md'
        text=f'# Fictional SecureBank demo policy: {title}\n\nNot official bank policy or regulatory guidance. Version 1.0.\n\n'
        text+='\n\n'.join(f'## {sid} | {title}\n{body}' for sid,body in sections)+'\n'
        (root/source).write_text(text,encoding='utf-8',newline='\n')
        manifest.append(dict(document_id=ident,document_title=title,version='1.0',effective_date='2026-10-24',classification='public',allowed_roles=['customer'],approved=True,current=True,source_file=source,sha256=hashlib.sha256((root/source).read_bytes()).hexdigest()))
    (root/'metadata'/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(f'Created {len(manifest)} fictional policy documents.')

if __name__=='__main__': main()
