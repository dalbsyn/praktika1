# Запросы для проверки работы сервиса

Предполагается, что база данных заполнена какими-то данными

## Примечания

- Тут для проверок используется `curl`;
- Если в URL будет строка вида `$(uuidgen)`, то это означает, что на его месте должна быть строка в виде UUID. `uuidgen` - команда, которая генерирует UUID в Linux-дистрибутивах. В Python UUID можно создать с помощью встроенного модуля `uuid` и функций `uuid1()` или `uuid4()`.

## Удержание средств

```sh
curl -X POST -H "Content-Type: application/json" -d '{
    "account_identifier": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
    "amount": 100,
    "description": "Test"
}' http://localhost:5000/api/operation/$(uuidgen)/hold
```

## Списание средств

Предварительно должно быть выполнено "Удержание средств".

```sh
curl -X POST http://localhost:5000/api/operation/YYYYYYYY-YYYY-YYYY-YYYY-YYYYYYYYYYYY/charge
```

Где `YYYYYYYY-YYYY-YYYY-YYYY-YYYYYYYYYYYY` - UUID транзакции, которая в состоянии удержания средств.

## Отмена операции

Предварительно должно быть выполнено "Удержание средств".

```sh
curl -X POST http://localhost:5000/api/operation/YYYYYYYY-YYYY-YYYY-YYYY-YYYYYYYYYYYY/cancel
```

Где `YYYYYYYY-YYYY-YYYY-YYYY-YYYYYYYYYYYY` - UUID транзакции, которая в состоянии удержания средств.

## Возврат средств

Предварительно должны быть выполнены "Удержание средств" и "Списание средств".

```sh
curl -X POST -H "Content-Type: application/json" -d '{
    "description": "Test"
}' http://localhost:5000/api/operation/YYYYYYYY-YYYY-YYYY-YYYY-YYYYYYYYYYYY/refund
```

Где `YYYYYYYY-YYYY-YYYY-YYYY-YYYYYYYYYYYY` - UUID транзакции, которая завершена.
