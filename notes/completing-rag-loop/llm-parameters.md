# LLM Generation Parameters for Movie Recommendations

These are LLM generation parameters that control how the model behaves:

## Temperature (0.0 - 2.0)

Controls creativity vs. consistency

- **0.0** = Deterministic - Always picks most likely next word
- **0.7** = Balanced - Good mix of consistency and creativity
- **1.0** = Creative - More diverse, interesting responses
- **2.0** = Chaotic - Very random, potentially incoherent

```python
# For movie recommendations:
"temperature": 0.7  # Sweet spot for creative but sensible suggestions
```

**Example at different temperatures:**
- **0.0**: "I recommend Blade Runner (1982)" (predictable)
- **0.7**: "You might enjoy Her (2013) - it's thoughtful sci-fi with..."
- **1.5**: "What about that movie with the robot feelings thing?"

## top_p (0.0 - 1.0)

"Nucleus sampling" - controls vocabulary diversity

- **0.1** = Only consider top 10% most likely words (focused)
- **0.9** = Consider top 90% of probability mass (diverse)
- **1.0** = Consider all possible words (maximum diversity)

```python
"top_p": 0.9  # Good balance - avoids weird words but allows creativity
```

## num_predict (integer)

Maximum number of tokens to generate

- **50** = Short response (1-2 sentences)
- **200** = Medium response (1 paragraph)
- **800** = Long response (4-5 movie recommendations with explanations)

```python
"num_predict": 800  # Enough for detailed movie recommendations
```

## top_k (integer, optional)

Alternative to top_p - limits to top K most likely words

- **40** = Only consider 40 most likely next words
- **100** = Broader vocabulary selection

## Optimal Settings for Movie Recommendations

```python
"options": {
    "temperature": 0.7,    # Creative but coherent recommendations
    "top_p": 0.9,          # Diverse vocabulary, avoid weird words  
    "num_predict": 800,    # 4-5 detailed recommendations
    "top_k": 40            # Focused vocabulary selection
}
```

### Why these values?

- **High enough creativity** to suggest interesting, non-obvious movies
- **Low enough temperature** to stay relevant and accurate
- **Enough tokens** for detailed explanations and reasoning
- **Focused vocabulary** to avoid weird or inappropriate suggestions

Over time, we can experiment with different values to see how they affect movie recommendation quality and user satisfaction.

## Parameter Impact on Recommendations

| Setting | Conservative | Balanced (Current) | Creative |
|---------|-------------|-------------------|-----------|
| Temperature | 0.3 | 0.7 | 1.2 |
| Result | Safe, predictable picks | Good mix of known/discovery | Unusual, experimental picks |
| Use Case | Playing it safe | General recommendations | Adventurous users |

The current balanced approach works well for most users while still providing interesting suggestions.