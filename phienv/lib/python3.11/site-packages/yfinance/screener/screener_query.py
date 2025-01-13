from abc import ABC, abstractmethod
import numbers
from typing import List, Union, Dict

from yfinance.const import EQUITY_SCREENER_EQ_MAP, EQUITY_SCREENER_FIELDS
from yfinance.exceptions import YFNotImplementedError
from ..utils import dynamic_docstring, generate_list_table_from_dict

class Query(ABC):
    def __init__(self, operator: str, operand: Union[numbers.Real, str, List['Query']]):
        self.operator = operator
        self.operands = operand

    @abstractmethod
    def to_dict(self) -> Dict:
        raise YFNotImplementedError('to_dict() needs to be implemented by children classes')

class EquityQuery(Query):
    """
    The `EquityQuery` class constructs filters for stocks based on specific criteria such as region, sector, exchange, and peer group.

    The queries support operators: `GT` (greater than), `LT` (less than), `BTWN` (between), `EQ` (equals), and logical operators `AND` and `OR` for combining multiple conditions.

    Example:
        Screen for stocks where the end-of-day price is greater than 3.
        
        .. code-block:: python

            gt = yf.EquityQuery('gt', ['eodprice', 3])

        Screen for stocks where the average daily volume over the last 3 months is less than a very large number.

        .. code-block:: python

            lt = yf.EquityQuery('lt', ['avgdailyvol3m', 99999999999])

        Screen for stocks where the intraday market cap is between 0 and 100 million.

        .. code-block:: python

            btwn = yf.EquityQuery('btwn', ['intradaymarketcap', 0, 100000000])

        Screen for stocks in the Technology sector.

        .. code-block:: python

            eq = yf.EquityQuery('eq', ['sector', 'Technology'])

        Combine queries using AND/OR.

        .. code-block:: python

            qt = yf.EquityQuery('and', [gt, lt])
            qf = yf.EquityQuery('or', [qt, btwn, eq])
    """
    def __init__(self, operator: str, operand: Union[numbers.Real, str, List['EquityQuery']]):
        """
        .. seealso::
            
            :attr:`EquityQuery.valid_operand_fields <yfinance.EquityQuery.valid_operand_fields>`
                supported operand values for query
            :attr:`EquityQuery.valid_eq_operand_map <yfinance.EquityQuery.valid_eq_operand_map>`
                supported `EQ query operand parameters`
        """
        operator = operator.upper()

        if not isinstance(operand, list):
            raise TypeError('Invalid operand type')
        if len(operand) <= 0:
            raise ValueError('Invalid field for Screener')
            
        if operator in {'OR','AND'}: 
            self._validate_or_and_operand(operand)
        elif operator == 'EQ': 
            self._validate_eq_operand(operand)
        elif operator == 'BTWN': 
            self._validate_btwn_operand(operand)
        elif operator in {'GT','LT'}: 
            self._validate_gt_lt(operand)
        else: 
            raise ValueError('Invalid Operator Value')

        self.operator = operator
        self.operands = operand
        self._valid_eq_operand_map = EQUITY_SCREENER_EQ_MAP
        self._valid_operand_fields = EQUITY_SCREENER_FIELDS
    
    @dynamic_docstring({"valid_eq_operand_map_table": generate_list_table_from_dict(EQUITY_SCREENER_EQ_MAP)})
    @property
    def valid_eq_operand_map(self) -> Dict:
        """
        Valid Operand Map for Operator "EQ"
        {valid_eq_operand_map_table}
        """
        return self._valid_eq_operand_map

    @dynamic_docstring({"valid_operand_fields_table": generate_list_table_from_dict(EQUITY_SCREENER_FIELDS)})
    @property
    def valid_operand_fields(self) -> Dict:
        """
        Valid Operand Fields
        {valid_operand_fields_table}
        """
        return self._valid_operand_fields
    
    def _validate_or_and_operand(self, operand: List['EquityQuery']) -> None:
        if len(operand) <= 1: 
            raise ValueError('Operand must be length longer than 1')
        if all(isinstance(e, EquityQuery) for e in operand) is False: 
            raise TypeError('Operand must be type EquityQuery for OR/AND')

    def _validate_eq_operand(self, operand: List[Union[str, numbers.Real]]) -> None:
        if len(operand) != 2:
            raise ValueError('Operand must be length 2 for EQ')
        
        if  not any(operand[0] in fields_by_type for fields_by_type in EQUITY_SCREENER_FIELDS.values()):
            raise ValueError('Invalid field for Screener')
        if operand[0] not in EQUITY_SCREENER_EQ_MAP:
            raise ValueError('Invalid EQ key')
        if operand[1] not in EQUITY_SCREENER_EQ_MAP[operand[0]]:
            raise ValueError('Invalid EQ value')
    
    def _validate_btwn_operand(self, operand: List[Union[str, numbers.Real]]) -> None:
        if len(operand) != 3: 
            raise ValueError('Operand must be length 3 for BTWN')
        if  not any(operand[0] in fields_by_type for fields_by_type in EQUITY_SCREENER_FIELDS.values()):
            raise ValueError('Invalid field for Screener')
        if isinstance(operand[1], numbers.Real) is False:
            raise TypeError('Invalid comparison type for BTWN')
        if isinstance(operand[2], numbers.Real) is False:
            raise TypeError('Invalid comparison type for BTWN')

    def _validate_gt_lt(self, operand: List[Union[str, numbers.Real]]) -> None:
        if len(operand) != 2:
            raise ValueError('Operand must be length 2 for GT/LT')
        if  not any(operand[0] in fields_by_type for fields_by_type in EQUITY_SCREENER_FIELDS.values()):
            raise ValueError('Invalid field for Screener')
        if isinstance(operand[1], numbers.Real) is False:
            raise TypeError('Invalid comparison type for GT/LT')

    def to_dict(self) -> Dict:
        return {
            "operator": self.operator,
            "operands": [operand.to_dict() if isinstance(operand, EquityQuery) else operand for operand in self.operands]
        }