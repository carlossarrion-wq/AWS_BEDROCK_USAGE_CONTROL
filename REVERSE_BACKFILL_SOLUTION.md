# Reverse Backfill Solution: CloudWatch → DynamoDB

## Updated Problem Analysis

Based on your feedback that **CloudWatch has more historical data than DynamoDB**, the issue is the reverse of what I initially thought:

### The Real Issue
- **CloudWatch has complete historical data** ✅
- **DynamoDB has incomplete/missing historical data** ❌
- **Dashboard reads from CloudWatch** ✅ (so dashboard should work)
- **But some users show missing data** ❌

### Possible Root Causes

1. **DynamoDB TTL (Time To Live)** - Old records are being automatically deleted
2. **DynamoDB table was recreated** - Lost historical data but CloudWatch retained it
3. **Inconsistent data sources** - Different systems writing to CloudWatch vs DynamoDB
4. **Recent DynamoDB implementation** - CloudWatch has data from before DynamoDB was implemented

## Investigation Steps

### 1. Run the Data Discrepancy Analysis

I've created a script to compare CloudWatch and DynamoDB data:

```bash
python investigate_data_discrepancy.py
```

This will:
- Compare data between CloudWatch and DynamoDB for all users
- Show exactly which users have discrepancies
- Identify patterns in the missing data
- Check if DynamoDB TTL is causing data deletion

### 2. Check DynamoDB TTL Settings

The most likely cause is that DynamoDB has TTL (Time To Live) enabled, which automatically deletes old records. Check this:

```bash
aws dynamodb describe-time-to-live --table-name bedrock_user_daily_usage
```

If TTL is enabled, you'll see something like:
```json
{
    "TimeToLiveDescription": {
        "TimeToLiveStatus": "ENABLED",
        "AttributeName": "ttl"
    }
}
```

## Solution Options

### Option 1: Reverse Backfill (CloudWatch → DynamoDB)

If CloudWatch has the complete data, we can backfill DynamoDB from CloudWatch:

```bash
# Create a reverse backfill script
python reverse_backfill_dynamodb.py
```

This would:
- Read historical data from CloudWatch
- Populate missing records in DynamoDB
- Ensure both data sources are synchronized

### Option 2: Fix TTL Configuration

If TTL is causing data deletion:

1. **Disable TTL** (if not needed):
   ```bash
   aws dynamodb update-time-to-live \
       --table-name bedrock_user_daily_usage \
       --time-to-live-specification Enabled=false
   ```

2. **Adjust TTL duration** (if TTL is needed):
   - Increase the TTL value to retain data longer
   - Update the Lambda function to set appropriate TTL values

### Option 3: Dashboard Data Source Strategy

Since CloudWatch has the complete data:

1. **Keep dashboard reading from CloudWatch** (current approach)
2. **Use DynamoDB only for operational data** (current usage, blocking status)
3. **Ensure new data goes to both sources** (already implemented in the Lambda fix)

## Recommended Action Plan

### Step 1: Investigate
```bash
# Run the investigation script
python investigate_data_discrepancy.py

# Check TTL settings
aws dynamodb describe-time-to-live --table-name bedrock_user_daily_usage
```

### Step 2: Based on Investigation Results

**If TTL is the cause:**
- Decide whether to disable TTL or adjust retention period
- Consider the storage costs vs data retention needs

**If table was recreated:**
- Run reverse backfill from CloudWatch to DynamoDB
- Ensure both sources stay synchronized going forward

**If different systems are involved:**
- Identify all systems writing to CloudWatch
- Ensure consistency in data publishing

### Step 3: Implement Fix

The Lambda function fix I provided earlier is still valid - it ensures that **going forward**, all new Bedrock usage will be recorded in both DynamoDB and CloudWatch simultaneously.

For historical data, we need to determine the best approach based on the investigation results.

## Why This Makes Sense

Your observation that "CloudWatch has more historical data than DynamoDB" actually explains the dashboard behavior:

- **Some users appear in CloudWatch** → Dashboard shows their data
- **Some users missing from CloudWatch** → Dashboard shows no data for them
- **DynamoDB has recent data only** → Real-time operations work, but historical view is incomplete

The solution is to ensure data consistency between both sources, with CloudWatch being the "source of truth" for historical data.

## Next Steps

1. **Run the investigation script** to understand the exact discrepancy
2. **Check TTL settings** to see if that's causing data loss
3. **Decide on the backfill strategy** based on findings
4. **Implement the appropriate fix**

Would you like me to create the reverse backfill script (CloudWatch → DynamoDB) or would you prefer to run the investigation first?
