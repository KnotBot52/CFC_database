import pandas as pd
import sys

def main():
    try:
        df = pd.read_csv("vegan_amazon_products.csv")
    except FileNotFoundError:
        print("Error: vegan_amazon_products.csv not found.")
        sys.exit(1)

    print(f"Original product count: {len(df)}")

    # Make names lowercase for easy matching
    df['lower_name'] = df['Name'].str.lower()

    # Strict exclusion list for products that are definitely not vegan
    # These often slip into Amazon searches for "vegan alternatives" or sponsored ads
    exclusions = [
        "whey", "casein", "dairy", "milk", "cheese", "butter", "yogurt", "cream",
        "beef", "chicken", "pork", "turkey", "fish", "salmon", "tuna", "shrimp", "seafood",
        "bone broth", "collagen", "gelatin", "honey", "beeswax", "lard", "tallow",
        "egg", "eggs", "mayonnaise", "leather", "wool", "silk"
    ]
    
    # Exceptions that might trigger exclusion but are actually vegan
    # e.g., "vegan cheese", "dairy free milk"
    exceptions = [
        "vegan", "plant based", "plant-based", "dairy free", "dairy-free",
        "meatless", "meat free", "meat-free", "egg free", "egg-free",
        "artificial", "imitation", "mock"
    ]

    # Function to check if a product should be excluded
    def is_vegan(name):
        # If it explicitly says vegan or plant-based, we'll generally trust it over the exclusion list
        # (e.g. "Vegan Cheese" contains "cheese" but is fine)
        # However, some products say "goes well with beef" but are "vegan", so we must be careful.
        
        has_exclusion = any(ex in name for ex in exclusions)
        if not has_exclusion:
            return True # No bad words found
            
        # It has a bad word. Does the brand specifically label it as an alternative?
        has_exception = any(exc in name for exc in exceptions)
        if has_exception:
            return True # It says "vegan cheese" or "dairy free milk"
            
        return False # Has a bad word and no saving "vegan" modifier

    # Filter the dataframe
    df['is_vegan'] = df['lower_name'].apply(is_vegan)
    
    # Show some examples of things we are dropping
    dropped = df[df['is_vegan'] == False]
    if len(dropped) > 0:
        print(f"\nDropping {len(dropped)} potentially non-vegan items. Examples:")
        for idx, row in dropped.head(10).iterrows():
            print(f"- {row['Name']}")

    # Keep only the valid ones
    cleaned_df = df[df['is_vegan'] == True].copy()
    
    # Clean up the helper columns
    cleaned_df = cleaned_df.drop(columns=['lower_name', 'is_vegan'])
    
    print(f"\nFinal cleaned product count: {len(cleaned_df)}")
    
    cleaned_df.to_csv("verified_vegan_products.csv", index=False)
    print("Saved clean list to 'verified_vegan_products.csv'")

if __name__ == "__main__":
    main()
