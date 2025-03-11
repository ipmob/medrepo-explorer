TOOL_CALL_GEMINI = {
    "tools": [{
        "function_declarations": [{
            "name": "extract_medical_report",
            "description": "Extract raw data from medical laboratory reports",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_details": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "age": {"type": "integer"},
                            "sex": {"type": "string"},
                            "reg_no": {"type": "string"},
                            "registration_date": {"type": "string"}
                        },
                        "required": ["name", "age", "sex"]
                    },
                    "report_details": {
                        "type": "object",
                        "properties": {
                            "request_no": {"type": "string"},
                            "bill_no": {"type": "string"},
                            "referral_by": {"type": "string"},
                            "reporting_date": {"type": "string"},
                            "specimen": {
                                "type": "string",
                                "description": "Description of the specimen (e.g., 'BLOOD / EDTA WHOLE BLOOD / SERUM')"
                            }
                        }
                    },
                    "laboratory_details": {
                        "type": "object",
                        "properties": {
                            "entered_by": {"type": "string"},
                            "verified_by": {"type": "string"},
                            "date": {"type": "string"},
                            "time": {"type": "string"},
                            "final_report": {
                                "type": "object",
                                "properties": {
                                    "date": {"type": "string"},
                                    "signature": {"type": "string"},
                                    "title": {"type": "string"}
                                }
                            }
                        }
                    },
                    "test_results": {
                        "type": "object",
                        "properties": {
                            "test_type": {
                                "type": "string", 
                                "enum": [
                                    "blood-tests-for-inflammation",
                                    "cbc-blood-test",
                                    "metabolic-panel",
                                    "thyroid-panel-test", 
                                    "urinalysis-test"
                                ]
                            },
                            "indicators": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string", "description": "Standardized indicator name (e.g., HEMOGLOBIN)"},
                                        "value": {"type": "string", "description": "The measured value of the indicator"},
                                        "reference": {"type": "string", "description": "The reference range for this indicator"},
                                        "methodology": {"type": "string", "description": "The testing methodology used"},
                                        "flag": {
                                            "type": "string",
                                            "enum": ["normal", "low", "high", "critical_low", "critical_high", "undetermined"],
                                            "description": "Flag indicating if the value is within normal range or abnormal"
                                        },
                                        "original_name": {"type": "string", "description": "The exact name as it appears in the report"},
                                        "original_value": {"type": "string", "description": "The exact value as it appears in the report"},
                                        "original_unit": {"type": "string", "description": "The exact unit as it appears in the report"},
                                        "original_reference": {"type": "string", "description": "The exact reference range as it appears in the report"}
                                    },
                                    "required": ["name", "value", "reference"]
                                }
                            },
                            "analysis": {
                                "type": "object",
                                "properties": {
                                    "summary": {"type": "string"},
                                    "recommendations": {"type": "string"},
                                    "markdown": {"type": "string"}
                                },
                                "required": ["summary"]
                            }
                        },
                        "required": ["test_type", "indicators"]
                    }
                },
                "required": ["patient_details", "test_results"]
            }
        }]
    }]
}