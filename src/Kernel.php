<?php

declare(strict_types=1);

namespace App;

use App\Container\Container;
use App\Http\Request;
use App\Http\Response;
use App\Http\Router;
use App\Shared\Exception\DomainException;
use App\Shared\Exception\NotFoundException;
use Throwable;

/**
 * Punkt wejścia aplikacji: buduje kontener, ładuje trasy i zamienia wyjątki na odpowiedzi HTTP.
 */
final class Kernel
{
    private Container $container;

    public function __construct(private readonly string $projectDir)
    {
        $this->container = new Container();
        $services = require $projectDir . '/config/services.php';
        $services($this->container, $projectDir);
    }

    public function container(): Container
    {
        return $this->container;
    }

    public function handle(Request $request): Response
    {
        $router = new Router();
        $routes = require $this->projectDir . '/config/routes.php';
        $routes($router);

        try {
            return $router->dispatch($request, $this->container);
        } catch (NotFoundException $e) {
            return Response::json(['error' => $e->getMessage()], 404);
        } catch (DomainException $e) {
            return Response::json(['error' => $e->getMessage()], 422);
        } catch (Throwable $e) {
            return Response::json(['error' => 'Internal server error'], 500);
        }
    }
}
