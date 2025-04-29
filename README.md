# API Poison Dust

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Steps

1. Clone the repository:

    ```bash
    git clone https://github.com/yourusername/api_poison_dust.git
    cd api_poison_dust
    ```

2. Create and activate a virtual environment:

    ```bash
    # Windows
    python -m venv venv
    venv\Scripts\activate

    # Linux/Mac
    python3 -m venv venv
    source venv/bin/activate
    ```

3. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

4. Run the API:

    ```bash
    uvicorn src.backend.app:app --reload
    ```

## API Usage

### Check Addresses Endpoint

**POST** `/check-addresses`

Analyzes two Solana addresses to detect potential risks.

#### Request Body

```json
{
  "from_address_check": "5LbwC1ewY3Sca7T8CwzX9wsjvwMAHbdRo6SCQL8j7EWc",
  "to_address_check": "5CNkMChs6E3YgAt5riRAfJTChxesVgYwbkhPwpnsznxY"
}
```

#### Response

```json
{
  "is_risky": true,
  "risk_level": 90,
  "message": "Suspicious address: similar to 5CNkk2gQKT42qeVVZo69PMoLw2XKG8xsVebBDKGo3DpY (original address) - Low value SOL transaction"
}
```

### Risk Assessment

- `is_risky`: Boolean indicating if the address is considered risky
- `risk_level`: Risk score from 0 to 100
- `message`: Detailed explanation of the risk assessment

### Risk Factors

- Similar address patterns
- Low value SOL transactions (< 0.001 SOL)
- Significantly lower transaction values compared to original address (5x lower)

## Example Usage with cURL

```bash
curl -X POST "http://localhost:8000/check-addresses" \
     -H "Content-Type: application/json" \
     -d '{
         "from_address_check": "5LbwC1ewY3Sca7T8CwzX9wsjvwMAHbdRo6SCQL8j7EWc",
         "to_address_check": "5CNkMChs6E3YgAt5riRAfJTChxesVgYwbkhPwpnsznxY"
     }'
```
