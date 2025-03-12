"""
Application Startup Module

This module contains functions that should be executed during application startup.
It handles initialization of various components, loading resources, and other startup tasks.
"""
from fastapi import FastAPI
from typing import Callable

from app.utils.logger import logger
from app.loinc.loinc_mapper import get_loinc_mapper
from app.config.constants import LOINC_CSV_PATH, LOINC_INDEX_PATH


def create_startup_handler() -> Callable:
    """
    Creates a startup handler function for FastAPI.
    
    Returns:
        A function that will be executed when the FastAPI application starts
    """
    async def startup() -> None:
        """
        Function that is executed during application startup.
        Initializes various components of the application.
        """
        logger.info("Starting application initialization...")
        
        # Initialize LOINC mapper
        logger.info("Initializing LOINC mapper...")
        try:
            # Get the mapper instance - this will create the index if it doesn't exist
            loinc_mapper = get_loinc_mapper(
                loinc_path=str(LOINC_CSV_PATH),
                index_path=str(LOINC_INDEX_PATH)
            )
            logger.info(f"LOINC mapper initialized successfully. Index contains {len(loinc_mapper.loinc_index)} entries")
        except Exception as e:
            logger.error(f"Failed to initialize LOINC mapper: {str(e)}")
            logger.warning("Application will continue without LOINC mapping functionality")
        
        logger.info("Application initialization completed")
    
    return startup


def create_shutdown_handler() -> Callable:
    """
    Creates a shutdown handler function for FastAPI.
    
    Returns:
        A function that will be executed when the FastAPI application shuts down
    """
    async def shutdown() -> None:
        """
        Function that is executed during application shutdown.
        Performs cleanup tasks.
        """
        logger.info("Shutting down application...")
        
        # Add any cleanup tasks here
        
        logger.info("Application shutdown completed")
    
    return shutdown


def register_startup_and_shutdown_events(app: FastAPI) -> None:
    """
    Register startup and shutdown event handlers with the FastAPI application.
    
    Args:
        app: The FastAPI application instance
    """
    app.add_event_handler("startup", create_startup_handler())
    app.add_event_handler("shutdown", create_shutdown_handler()) 