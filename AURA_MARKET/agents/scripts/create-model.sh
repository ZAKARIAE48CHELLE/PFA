#!/bin/bash
echo "════════════════════════════════════════"
echo "  AuraMarket — Creating custom model"
echo "════════════════════════════════════════"
echo ""
cd "$(dirname "$0")/../src/main/resources"
echo "Working directory: $(pwd)"
echo ""
echo "Creating auramarket-agent from Modelfile..."
ollama create auramarket-agent -f Modelfile
echo ""
echo "════════════════════════════════════════"
echo "  Verifying installation..."
echo "════════════════════════════════════════"
ollama list
echo ""
echo "Done!"
