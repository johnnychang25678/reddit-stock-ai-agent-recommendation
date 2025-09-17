import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

# Now this import won't create a database connection
from stock_ai.workflows.persistence.sql_alchemy_persistence import SqlAlchemyPersistence


class MockModel:
    __name__ = "MockModel"
    __table__ = Mock()
    
    # Mock the column attributes to behave like SQLAlchemy columns
    id = Mock()
    name = Mock()
    
    def __init__(self):
        # Make getattr work properly for dynamic column access
        pass


@pytest.fixture
def mock_registry():
    return {"test_table": MockModel}


@pytest.fixture
def persistence(mock_registry):
    return SqlAlchemyPersistence(mock_registry)


class TestSqlAlchemyPersistence:
    @patch('stock_ai.workflows.persistence.sql_alchemy_persistence.select')
    @patch('stock_ai.workflows.persistence.sql_alchemy_persistence.get_session')
    def test_get_with_filters(self, mock_get_session, mock_select, persistence):
        # Arrange
        mock_session = Mock(spec=Session)
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        # Mock the select statement and its chaining
        mock_stmt = Mock()
        mock_select.return_value = mock_stmt
        mock_stmt.where.return_value = mock_stmt
        
        # Mock the session.scalars chain
        mock_session.scalars.return_value.all.return_value = ["result1", "result2"]
        
        # Act
        result = persistence.get("test_table", name="test")
        
        # Assert
        assert result == ["result1", "result2"]
        mock_select.assert_called_once_with(MockModel)
        mock_stmt.where.assert_called_once()
        mock_session.scalars.assert_called_once_with(mock_stmt)

    @patch('stock_ai.workflows.persistence.sql_alchemy_persistence.get_session')
    def test_get_unknown_key(self, mock_get_session, persistence):
        with pytest.raises(KeyError, match="Unknown key 'unknown'"):
            persistence.get("unknown")

    @patch('stock_ai.workflows.persistence.sql_alchemy_persistence.select')
    @patch('stock_ai.workflows.persistence.sql_alchemy_persistence.get_session')
    def test_get_unknown_column(self, mock_get_session, mock_select, persistence):
        mock_session = Mock(spec=Session)
        mock_get_session.return_value.__enter__.return_value = mock_session

        # We won’t actually reach query execution, but keep select harmless
        mock_select.return_value = Mock()  # dummy stmt

        # No getattr patching needed; MockModel has no 'unknown_column'
        with pytest.raises(ValueError, match="Unknown column"):
            persistence.get("test_table", unknown_column="test")

    @patch('stock_ai.workflows.persistence.sql_alchemy_persistence.insert')
    @patch('stock_ai.workflows.persistence.sql_alchemy_persistence.get_session')
    def test_set_with_dict_list(self, mock_get_session, mock_insert, persistence):
        # Arrange
        mock_session = Mock(spec=Session)
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        mock_stmt = Mock()
        mock_insert.return_value = mock_stmt
        mock_stmt.values.return_value = mock_stmt
        
        test_data = [{"id": 1, "name": "test"}]
        
        # Act
        persistence.set("test_table", test_data)
        
        # Assert
        mock_insert.assert_called_once_with(MockModel)
        mock_stmt.values.assert_called_once_with(test_data)
        mock_session.execute.assert_called_once_with(mock_stmt)
        mock_session.commit.assert_called_once()

    def test_set_unknown_key(self, persistence):
        with pytest.raises(KeyError, match="Unknown key 'unknown'"):
            persistence.set("unknown", [])