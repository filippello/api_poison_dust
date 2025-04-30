### **Objectives & Scope**

We aim to solve the **address poisoning** problem. This occurs when a scammer sends a low-value transaction to a user's wallet **after** the user has previously received funds from a legitimate address. The scammer forges an address that **matches the first 4 characters** of the original sender’s address, hoping the user will confuse them when checking their transaction history and mistakenly send funds to the scammer’s wallet.

Our goal is to detect this threat **before the transaction is broadcasted**, in the fastest and most efficient way possible.


### **Technical Architecture**

To enable real-time detection of address poisoning attacks, we designed a lightweight and fast-check methodology that effectively handles most common scenarios.

Our API is designed to be integrated into a **wallet interface** or an **RPC-level security layer**. Once a transaction is initiated, the app extracts the following:

* `from_address_check`: the sender's address (origin wallet)

* `to_address_check`: the recipient's address (target wallet)

These two parameters are sent to our API. With them, we call **Solscan's** API endpoints to fetch relevant transaction history, using:

* `account/transfer` to get historical inbound transactions

* `transaction/detail` to analyze the transaction context

***

### **Data Flow & Logic**

Before the wallet signs or broadcasts a transaction, it queries our API.

Our backend performs two real-time API calls:

* [`GET /v2.0/account/transfer`](https://pro-api.solscan.io/v2.0/account/transfer)

* [`GET /v2.0/transaction/detail`](https://pro-api.solscan.io/v2.0/transaction/detail)

These allow us to:

* Identify all addresses that have previously **sent funds** to the origin wallet

* Track the **block number** of each first interaction

This data enables us to evaluate whether the recipient address is suspicious, and to do so **in real time** before the transaction is sent.

***

### **Architecture**


<img width="485" alt="Image" src="https://github.com/user-attachments/assets/a21e303e-8b24-4e5c-90b0-9e93f7f6b8e5" />


### **Challenges & Solutions**

One of the key challenges was avoiding **false positives** while maintaining high sensitivity to poisoning attacks. To solve this:

1. We calculate the **collision probability** of two addresses sharing the first 4 characters (≈ 0.0005), and consider only the **first address** seen on-chain with that prefix as trusted.

2. If the **first interaction** was a **low-value SOL transfer**, we raise the risk score to **90**.

3. If the transfer was in a **non-SOL token**, we estimate that a legitimate test transfer usually involves at least **$1**. Subsequent transfers must be at least **1/5** of that original value to be considered safe; otherwise, the risk is also set to **90**.

This layered logic helps reduce false positives and covers a wide range of poisoning patterns.

***

### **Impact & Relevance**

Our solution enhances **user protection** and **transactional security** in the Solana ecosystem by detecting address poisoning attacks **before they happen**.

By integrating into a wallet flow or acting as an **RPC middleware**, our API provides a real-time security check that warns users if they're about to send funds to a suspicious address. It can also be adapted to send alerts through alternate channels, reinforcing user safety across multiple entry points in the Solana ecosystem.


### **Test**

You can test the API online.
```bash
http://54.242.235.110:8000/check-addresses
```

user wallet ( from_address_check)
5LbwC1ewY3Sca7T8CwzX9wsjvwMAHbdRo6SCQL8j7EWc

wallet to check (to_address_check)


5CNkgg51xbb7kBkkLXXuLyBQcrJPpL2FU13xyY2qiQmY scam

5CNkk2gQKT42qeVVZo69PMoLw2XKG8xsVebBDKGo3DpY  Safe one

5CNkMChs6E3YgAt5riRAfJTChxesVgYwbkhPwpnsznxY scam

or

4yfu48qwim7hGzD3Nphzd2A6ThydzysfKi4wBPFSgnhY Safe one

4yfuQCL4fnNfSbBgqFcPTFn5GGZABDaEFQLhGpwjizcY scam

example:

```bash
curl -X 'POST' \
  'http://localhost:8000/check-addresses' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "from_address_check": "5LbwC1ewY3Sca7T8CwzX9wsjvwMAHbdRo6SCQL8j7EWc",
  "to_address_check": "5CNkMChs6E3YgAt5riRAfJTChxesVgYwbkhPwpnsznxY"
}'
```
