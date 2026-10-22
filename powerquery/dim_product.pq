// Query: dim_product
// Source: pDataFolder & "dim_product.csv" (UTF-8, comma-separated, header row)
// Grain: one row per product group. Key: product_key. Key 15 (All products, is_total = 1)
// is used only by fact_forecast rows with level = "Total".
// hs4_codes stays text: values like "61" and "6101,6102" must not be read as numbers.
let
    Source   = Csv.Document(File.Contents(pDataFolder & "dim_product.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
        {"product_key", Int64.Type}, {"chapter", type text}, {"product_group", type text},
        {"hs4_codes", type text}, {"market_scope", type text}, {"is_total", Int64.Type}
    }, "en-US"),
    // Label that tells the US and EU "Coats & jackets" etc. apart in slicers
    WithLabel = Table.AddColumn(Typed, "product_label", each [chapter] & " - " & [product_group], type text),
    Result   = WithLabel
in
    Result
